"""🏭 Industries & Businesses — /api/industry/*        Owner: TBD (see PLAN.md §7)

Real now: water risk of the taluk an industrial area / any map point falls in (provisional index).
Mock now: the industrial-area list (replace with KIADB data from data/raw/kiadb/), sector demand numbers.
TODO (PLAN.md §6):
  - KIADB areas with sectors + size -> water demand (sector intensity), groundwater dependence
  - production-disruption estimate, wastewater-reuse opportunities, location risk report (+ WRI Aqueduct)
"""
import numpy as np
from fastapi import APIRouter

from core.data import clamp_date, regions
from core.indicators import clean, taluk_indicators
from core.risk import taluk_risk

router = APIRouter(prefix="/api/industry", tags=["industry"])

# Mock until the KIADB file arrives: (area, taluk, main sector, est. demand MLD)
AREAS = [
    ("Peenya Industrial Area", "Bengaluru North", "Engineering", 6.0),
    ("Bommasandra", "Anekal", "Pharma / auto parts", 3.5),
    ("Whitefield EPIP", "Bengaluru East", "IT / electronics", 4.0),
    ("Narasapura", "Kolar", "Automotive", 2.5),
    ("Vemagal", "Kolar", "Manufacturing", 1.5),
    ("Tarihal (Hubballi)", "Hubballi", "Engineering", 1.2),
    ("Kolhar (Bidar)", "Bidar", "Food processing", 0.8),
    ("Baikampady (Mangaluru)", "Mangaluru", "Petrochemicals", 5.0),
    ("Hirehalli (Tumakuru)", "Tumakuru", "Food park / manufacturing", 1.0),
    ("Kumbalgodu", "Bengaluru South", "Textiles / garments", 1.2),
]


def _risk_row(i, ind, score, levels):
    return {"taluk_idx": int(i), "taluk": regions()[i]["name"], "district": regions()[i]["district"],
            "taluk_lat": regions()[i]["lat"], "taluk_lon": regions()[i]["lon"],
            "risk": levels[i], "stress": clean(score[i]), "rain_365d_dev_pct": clean(ind["rain_365d_dev_pct"][i]),
            "gw_depth_m": clean(ind["gw_depth_m"][i]), "gw_anom_m": clean(ind["gw_anom_m"][i])}


@router.get("/areas")
def api_areas(as_of: str | None = None):
    as_of = clamp_date(as_of)
    ind = taluk_indicators(as_of)
    rk = taluk_risk(as_of)
    score, levels = rk["score"], rk["levels"]
    by_name = {r["name"]: r["idx"] for r in regions()}
    areas = [{"area": a, "sector": s, "demand_mld": mld, **_risk_row(by_name[t], ind, score, levels)}
             for a, t, s, mld in AREAS if t in by_name]
    return {"as_of": as_of, "model": rk["model"], "mock": True,
            "note": "Area list and demand are placeholders until the KIADB data is cleaned", "areas": areas}


@router.get("/districts")
def api_districts(as_of: str | None = None):
    """M7: industrial water-disruption risk per district (KIADB land x M2 groundwater x M4 reservoirs)."""
    from usecases.industry_m7 import NORM_KL_PER_HA_DAY, districts
    as_of = clamp_date(as_of)
    rows = districts(as_of)
    tot = lambda k: round(sum(r[k] for r in rows), 1)
    return {"as_of": as_of, "model": "m7-transparent-score", "districts": rows,
            "totals": {"demand_mld": tot("demand_mld"), "water_at_risk_mld": tot("water_at_risk_mld"),
                       "reuse_potential_mld": tot("reuse_potential_mld"), "developed_acres": tot("developed_acres")},
            "assumptions": {"water_norm_kl_per_ha_day": NORM_KL_PER_HA_DAY, "surface_dependence_served": 0.6,
                            "surface_dependence_unserved": 0.15, "wastewater_share": 0.8, "recyclable_share": 0.7},
            "sources": {"real": ["KIADB developed land per district", "M2 groundwater forecast (2,664 wells)",
                                 "M4 reservoir forecast (NWDP dams)"],
                        "estimated": ["water use per hectare", "surface vs groundwater dependence"]}}


@router.get("/feasibility")
def api_feasibility(lat: float, lon: float, demand_kld: float, as_of: str | None = None,
                    gw_share: float | None = None, site_area_ha: float | None = None):
    """Can a factory needing `demand_kld` kL/day get its water at this point? Verdict, score and the evidence."""
    from fastapi import HTTPException
    from usecases.industry_site import feasibility
    if not 0 < demand_kld <= 500_000:
        raise HTTPException(400, "demand_kld must be between 0 and 500,000 kL/day")
    out = feasibility(lat, lon, demand_kld, clamp_date(as_of), gw_share, site_area_ha)
    if out is None:
        raise HTTPException(400, "That point is outside Karnataka")
    return out


@router.get("/location")
def api_location(lat: float, lon: float, as_of: str | None = None):
    """Water risk for any point: nearest taluk centre (good enough until point-in-polygon is added)."""
    as_of = clamp_date(as_of)
    regs = regions()
    lat_a = np.array([r["lat"] for r in regs])
    lon_a = np.array([r["lon"] for r in regs])
    i = int(np.argmin((lat_a - lat) ** 2 + ((lon_a - lon) * np.cos(np.radians(lat))) ** 2))
    ind = taluk_indicators(as_of)
    rk = taluk_risk(as_of)
    score, levels = rk["score"], rk["levels"]
    return {"as_of": as_of, "model": rk["model"], "lat": lat, "lon": lon, **_risk_row(i, ind, score, levels)}
