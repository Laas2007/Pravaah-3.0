"""🏙️ Urban Population — /api/urban/*        Owner: TBD (see PLAN.md §7)

The Bengaluru ward model (backend/model.py, endpoints /api/meta, /api/predict, /api/ward/...) is live and is
shown at /urban/bengaluru. Real now: taluk indicators for 11 cities, Cauvery dam storage (Bengaluru's piped supply).
Mock now: city population / supply.
TODO (PLAN.md §6):
  - city-level water balance (M2) with supply estimates; tanker-need ranking
  - Cauvery storage forecast (M4) -> piped-supply outlook for Bengaluru
  - demand forecast (M5), rainwater-harvesting calculator, leak detection on synthetic meters (M6)
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import model
from core.data import clamp_date, regions
from core.indicators import clean, taluk_indicators
from core.risk import taluk_risk
from core.reservoirs import CAUVERY_BENGALURU, combined_series, forecast_storage, reservoirs_end, storage_on

router = APIRouter(prefix="/api/urban", tags=["urban"])

# (city, taluk name, est. population 2026 in lakh, est. supply MLD) — population/supply are rough estimates (mock).
CITIES = [
    ("Bengaluru", "Bengaluru South", 140, 2225),
    ("Mysuru", "Mysuru", 12, 250),
    ("Hubballi-Dharwad", "Hubballi Urban", 11, 180),
    ("Mangaluru", "Mangaluru", 7, 160),
    ("Belagavi", "Belagavi", 6, 100),
    ("Kalaburagi", "Kalaburagi", 6, 90),
    ("Davanagere", "Davanagere", 5, 80),
    ("Ballari", "Ballari", 5, 70),
    ("Shivamogga", "Shivamogga", 4, 65),
    ("Tumakuru", "Tumakuru", 4, 60),
    ("Vijayapura", "Vijayapura", 4, 55),
]


@router.get("/cities")
def api_cities(as_of: str | None = None):
    as_of = clamp_date(as_of)
    ind = taluk_indicators(as_of)
    rk = taluk_risk(as_of)
    score, levels = rk["score"], rk["levels"]
    by_name = {r["name"]: r["idx"] for r in regions()}
    out = []
    for city, tname, pop, mld in CITIES:
        i = by_name.get(tname)
        out.append({
            "city": city, "taluk_idx": i, "live_ward_model": city == "Bengaluru",
            "lat": regions()[i]["lat"] if i is not None else None, "lon": regions()[i]["lon"] if i is not None else None,
            "risk": levels[i] if i is not None else None, "stress": clean(score[i]) if i is not None else None,
            "rain_365d_dev_pct": clean(ind["rain_365d_dev_pct"][i]) if i is not None else None,
            "gw_anom_m": clean(ind["gw_anom_m"][i]) if i is not None else None,
            "population_lakh": pop, "supply_mld": mld, "mock_fields": ["population_lakh", "supply_mld"],
        })
    return {"as_of": as_of, "model": rk["model"], "cities": out}


@router.get("/demand")
def api_demand(as_of: str | None = None):
    """M5 (estimated): Bengaluru demand / piped supply / borewell draw / tanker need per ward + 6-month outlook;
    other cities: demand vs estimated supply."""
    from usecases import urban_demand as ud
    d = ward_date(as_of)
    blr = dict(ud.bengaluru(d))
    blr.pop("wards")
    others = [{"city": c, **ud.city(pop, mld, d)} for c, _, pop, mld in CITIES if c != "Bengaluru"]
    return {"as_of": d, "model": "m5-estimated-demand", "bengaluru": blr, "cities": others,
            "assumptions": {"lpcd": ud.LPCD, "tanker_litres": ud.TANKER_L, "heat_elasticity_per_degC": ud.HEAT_PER_DEGC},
            "sources": {"real": ["IMD rain (Cauvery reliability, ward groundwater)", "ERA5 temperature"],
                        "estimated": ["population today", "pipe coverage", "commercial load", "city supply", "heat elasticity"]}}


@router.get("/leaks/demo")
def api_leaks_demo():
    """M6 on SYNTHETIC meters with planted leaks (no public meter data exists): detection precision / recall."""
    from usecases import urban_leaks as ul
    return ul.demo()


class LeakCheckIn(BaseModel):
    csv: str


@router.post("/leaks/check")
def api_leaks_check(body: LeakCheckIn):
    """M6 on an uploaded meter CSV (timestamp, litres per hour)."""
    from usecases import urban_leaks as ul
    if len(body.csv) > 2_000_000:
        raise HTTPException(400, "file too large (max ~2 MB)")
    try:
        return ul.check_csv(body.csv)
    except (ValueError, KeyError, IndexError) as e:
        raise HTTPException(400, f"could not read the CSV: {e}")


def ward_date(as_of: str | None) -> str:
    """Clamp a date to the Bengaluru ward model's record (its rain series can end a little earlier than the
    Karnataka climate data)."""
    import datetime as dt
    w = model.load_world()
    d = dt.date.fromisoformat(clamp_date(as_of))
    lo = dt.date.fromisoformat(w.dates[0]) + dt.timedelta(days=365)
    return min(max(d, lo), dt.date.fromisoformat(w.dates[-1])).isoformat()


@router.get("/wards")
def api_wards(as_of: str | None = None):
    """Bengaluru's 243 BBMP wards from the ward-level model (backend/model.py): days until groundwater shortage
    as a 25-75 % range, risk on the same 4-level scale. Polygons: /api/wards.geojson (property idx)."""
    d = ward_date(as_of)
    r = model.predict(d, model.Intervention(), False)
    return {"as_of": d, "model": "bengaluru-ward-balance", "data_until": r["data_until"],
            "wards": [{k: x[k] for k in ("idx", "name", "ward_no", "risk", "days_low", "days_mid", "days_high",
                                         "groundwater_pct")} for x in r["wards"]]}


@router.get("/cauvery")
def api_cauvery(as_of: str | None = None):
    """Storage in the four Cauvery dams that feed Bengaluru's piped supply (real, NWDP)."""
    as_of = clamp_date(as_of)
    dams = [s for s in storage_on(as_of) if s["name"] in CAUVERY_BENGALURU]
    series, capacity = combined_series(CAUVERY_BENGALURU, as_of)
    now = series[-1] if series else None
    fc = forecast_storage(CAUVERY_BENGALURU, as_of)
    if fc:   # actual combined storage at the forecast dates, when already known (Time Machine replays)
        for p in fc["points"]:
            later = combined_series(CAUVERY_BENGALURU, p["date"], days=0)[0] if p["date"] <= reservoirs_end() else []
            p["actual"] = later[-1]["storage_tmc"] if later and later[-1]["date"] == p["date"] else None
    return {"as_of": as_of, "dams": dams, "capacity_tmc": capacity, "series": series,
            "storage_tmc": now and now["storage_tmc"], "normal_tmc": now and now["normal_tmc"], "forecast": fc}
