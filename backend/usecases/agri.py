"""🌾 Agriculture & Farmers — /api/agri/*        Owner: TBD (see PLAN.md §7)

Real now: season rainfall vs normal, ET0, climatic water balance, groundwater for a taluk.
Mock now: crop recommendations (`mock: true`).
TODO (PLAN.md §6):
  - FAO-56 soil water balance (Kc x ET0) -> crop water stress + irrigation schedule
  - crop ranking: expected water (past-years ensemble + soil AWC) vs FAO seasonal need x M3 yield risk
  - sowing-date planner (P(stress) per sowing week over past rainfall years), yield-risk ranges (M3)
"""
import datetime as dt

from fastapi import APIRouter

from core.data import clamp_date, climate, taluk
from core.indicators import clean, rain_deviation, taluk_indicators
from core.risk import taluk_risk

router = APIRouter(prefix="/api/agri", tags=["agri"])

SEASONS = [("Kharif", 6, 9), ("Rabi", 10, 1), ("Summer", 2, 5)]   # (name, first month, last month)

# FAO-56 typical seasonal crop water need (mm) — real reference values; suitability below is still mock.
CROPS = [
    {"crop": "Ragi (finger millet)", "kn": "ರಾಗಿ", "water_need_mm": 400},
    {"crop": "Jowar (sorghum)", "kn": "ಜೋಳ", "water_need_mm": 500},
    {"crop": "Groundnut", "kn": "ಶೇಂಗಾ", "water_need_mm": 550},
    {"crop": "Tur (red gram)", "kn": "ತೊಗರಿ", "water_need_mm": 450},
    {"crop": "Maize", "kn": "ಮೆಕ್ಕೆಜೋಳ", "water_need_mm": 600},
    {"crop": "Paddy", "kn": "ಭತ್ತ", "water_need_mm": 1200},
    {"crop": "Sugarcane", "kn": "ಕಬ್ಬು", "water_need_mm": 1800},
]


def season_of(day: dt.date):
    for name, a, b in SEASONS:
        if (a <= b and a <= day.month <= b) or (a > b and (day.month >= a or day.month <= b)):
            start = dt.date(day.year - (1 if a > b and day.month <= b else 0), a, 1)
            return name, start
    raise AssertionError


@router.get("/taluk/{idx}")
def api_taluk(idx: int, as_of: str | None = None):
    as_of = clamp_date(as_of)
    t = taluk(idx)
    c = climate()
    t0 = c.index(as_of)
    day = dt.date.fromisoformat(as_of)
    season, start = season_of(day)
    n = (day - start).days + 1
    obs, normal, dev = rain_deviation(t0, n)
    et0 = float(c.et0[t0 - n + 1: t0 + 1, idx].sum())
    ind = taluk_indicators(as_of)
    rk = taluk_risk(as_of)
    score, levels = rk["score"], rk["levels"]
    expected = float(normal[idx]) * 1.0   # TODO: past-years ensemble for the rest of the season
    return {
        **t, "as_of": as_of, "model": rk["model"], "risk": levels[idx],
        "season": {"name": season, "start": start.isoformat(), "days": n,
                   "rain_mm": clean(obs[idx]), "normal_mm": clean(normal[idx]), "dev_pct": clean(dev[idx]),
                   "et0_mm": round(et0, 1), "water_balance_mm": round(float(obs[idx]) - et0, 1)},
        "groundwater": {"depth_m": clean(ind["gw_depth_m"][idx]), "anom_m": clean(ind["gw_anom_m"][idx]),
                        "month": ind["gw_month"][idx]},
        "crops": {"mock": True, "note": "Ranking logic not built yet (PLAN.md §6 Agri)",
                  "items": [{**cr, "fits_normal_rain": cr["water_need_mm"] <= expected + 200} for cr in CROPS]},
    }
