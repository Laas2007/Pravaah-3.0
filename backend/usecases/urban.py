"""🏙️ Urban Population — /api/urban/*        Owner: TBD (see PLAN.md §7)

The Bengaluru ward model (backend/model.py, endpoints /api/meta, /api/predict, /api/ward/...) is live and is
shown at /urban/bengaluru. Real now: taluk indicators for 11 cities, Cauvery dam storage (Bengaluru's piped supply).
Mock now: city population / supply.
TODO (PLAN.md §6):
  - city-level water balance (M2) with supply estimates; tanker-need ranking
  - Cauvery storage forecast (M4) -> piped-supply outlook for Bengaluru
  - demand forecast (M5), rainwater-harvesting calculator, leak detection on synthetic meters (M6)
"""
from fastapi import APIRouter

from core.data import clamp_date, regions
from core.indicators import clean, taluk_indicators
from core.risk import taluk_risk
from core.reservoirs import CAUVERY_BENGALURU, combined_series, storage_on

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


@router.get("/cauvery")
def api_cauvery(as_of: str | None = None):
    """Storage in the four Cauvery dams that feed Bengaluru's piped supply (real, NWDP)."""
    as_of = clamp_date(as_of)
    dams = [s for s in storage_on(as_of) if s["name"] in CAUVERY_BENGALURU]
    series, capacity = combined_series(CAUVERY_BENGALURU, as_of)
    now = series[-1] if series else None
    return {"as_of": as_of, "dams": dams, "capacity_tmc": capacity, "series": series,
            "storage_tmc": now and now["storage_tmc"], "normal_tmc": now and now["normal_tmc"],
            "forecast": None, "forecast_todo": "M4 storage forecast -> supply outlook (PLAN.md §5)"}
