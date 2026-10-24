"""M3 — crop water stress & yield risk, crop ranking, irrigation schedule, sowing planner (owner: P2).

Method (published, explainable):
  FAO-56 single crop coefficient: ETc = Kc(stage) x ET0, daily root-zone water balance; water stress Ks < 1 when the
  root-zone depletion exceeds RAW = p x TAW (TAW = soil available water x root depth).
  FAO-33 yield response: relative yield loss = Ky x (1 - season ETa / season ETc).
Inputs: REAL daily IMD rain (taluk) and ERA5 FAO ET0. Days after the forecast date use the same calendar days of each
of the previous 8 years (past years as possible futures, like M2/M4) -> a range per crop.
Estimated inputs (labelled): soil available water (black soils north of 15N ~170 mm/m, red/lateritic south ~110 mm/m;
SoilGrids would refine this), sowing dates (typical Karnataka kharif 20 Jun, rabi 15 Oct), crop coefficients/stage
lengths/Ky from FAO-56 Table 11-12 and FAO-33 (ragi, tur and rice Ky are approximations: not tabulated by FAO-33).
Checked against real district yields (DES 2024-25) in train/validate_crops.py -> models/m3_card.json.
"""
from __future__ import annotations

import datetime as dt
from functools import lru_cache

import numpy as np

from core.data import climate, regions

SCENARIO_YEARS = 8
# crop: (Kc ini, Kc mid, Kc end, stage days ini/dev/mid/late, Ky, root depth m, p, seasons, Kannada name)
CROPS = {
    "Rice (paddy)":        (1.05, 1.20, 0.90, (30, 30, 60, 30), 1.20, 0.6, 0.20, ("kharif", "summer"), "ಭತ್ತ"),
    "Maize":               (0.30, 1.20, 0.35, (20, 35, 40, 30), 1.25, 1.0, 0.55, ("kharif", "rabi"), "ಮೆಕ್ಕೆಜೋಳ"),
    "Jowar (sorghum)":     (0.30, 1.00, 0.55, (20, 35, 40, 30), 0.90, 1.2, 0.55, ("kharif", "rabi"), "ಜೋಳ"),
    "Ragi (finger millet)": (0.30, 1.00, 0.30, (20, 30, 40, 30), 1.00, 1.0, 0.55, ("kharif",), "ರಾಗಿ"),
    "Bajra (pearl millet)": (0.30, 1.00, 0.30, (15, 25, 40, 25), 1.00, 1.0, 0.55, ("kharif",), "ಸಜ್ಜೆ"),
    "Tur (red gram)":      (0.40, 1.00, 0.45, (20, 40, 80, 30), 1.00, 1.2, 0.50, ("kharif",), "ತೊಗರಿ"),
    "Urad (black gram)":   (0.40, 1.05, 0.35, (15, 25, 25, 10), 1.15, 0.7, 0.45, ("kharif",), "ಉದ್ದು"),
    "Moong (green gram)":  (0.40, 1.05, 0.35, (15, 25, 25, 10), 1.15, 0.7, 0.45, ("kharif", "summer"), "ಹೆಸರು"),
    "Groundnut":           (0.40, 1.15, 0.60, (25, 35, 45, 25), 0.70, 0.6, 0.50, ("kharif", "summer"), "ಶೇಂಗಾ"),
    "Cotton":              (0.35, 1.18, 0.60, (30, 50, 60, 55), 0.85, 1.2, 0.65, ("kharif",), "ಹತ್ತಿ"),
    "Sugarcane":           (0.40, 1.25, 0.75, (35, 60, 180, 90), 1.20, 1.4, 0.65, ("kharif",), "ಕಬ್ಬು"),
    "Gram (chickpea)":     (0.40, 1.00, 0.35, (20, 30, 35, 15), 1.00, 0.8, 0.50, ("rabi",), "ಕಡಲೆ"),
    "Wheat":               (0.40, 1.15, 0.30, (20, 30, 50, 30), 1.05, 1.2, 0.55, ("rabi",), "ಗೋಧಿ"),
}
SOWING = {"kharif": (6, 20), "rabi": (10, 15), "summer": (1, 15)}     # (month, day), typical for Karnataka


def season_for(day: dt.date) -> tuple[str, dt.date]:
    """Current or upcoming season and its sowing date for a forecast date."""
    if day.month in (3, 4, 5, 6, 7, 8, 9):
        return "kharif", dt.date(day.year, *SOWING["kharif"])
    if day.month in (10, 11, 12):
        return "rabi", dt.date(day.year, *SOWING["rabi"])
    return "rabi", dt.date(day.year - 1, *SOWING["rabi"])


def awc_mm_per_m(idx: int) -> float:
    """Soil available water (estimated): black cotton soils of the north hold more water than southern red soils."""
    return 170.0 if regions()[idx]["lat"] > 15.0 else 110.0


def kc_curve(crop: str) -> np.ndarray:
    kci, kcm, kce, (li, ld, lm, ll), *_ = CROPS[crop]
    return np.concatenate([np.full(li, kci), np.linspace(kci, kcm, ld), np.full(lm, kcm), np.linspace(kcm, kce, ll)])


@lru_cache(maxsize=4096)
def _weather(idx: int, sow_iso: str, length: int, as_of_iso: str) -> tuple[np.ndarray, np.ndarray, list[int]]:
    """Rain and ET0 for each day of the season (scenarios x days): observed up to as_of, then each earlier year's
    same calendar days. Returns (rain, et0, scenario_offsets_years)."""
    c = climate()
    d0 = dt.date.fromisoformat(c.dates[0])
    n = len(c.dates)
    sow = dt.date.fromisoformat(sow_iso)
    as_of = dt.date.fromisoformat(as_of_iso)
    s_idx = (sow - d0).days
    known = max(0, min(length, (as_of - sow).days + 1))          # season days already observed on as_of
    scen = [y for y in range(1, SCENARIO_YEARS + 1) if s_idx + known - 365 * y >= 0 and s_idx + length - 365 * y <= n]
    if known >= length:
        scen = [0]
    j = np.arange(length)
    T = np.where(j[None, :] < known, s_idx + j[None, :], s_idx + j[None, :] - 365 * np.array(scen)[:, None])
    T = np.clip(T, 0, n - 1)
    return c.rain[T, idx].astype(float), c.et0[T, idx].astype(float), scen


def water_balance(idx: int, crop: str, sow: dt.date, as_of: dt.date, irrigate: bool = False):
    """FAO-56 daily root-zone balance for every scenario (vectorised). Returns dict of arrays (scenarios,)."""
    kc = kc_curve(crop)
    L = len(kc)
    R, E, scen = _weather(idx, sow.isoformat(), L, as_of.isoformat())
    _, _, _, _, ky, zr, p, *_ = CROPS[crop]
    taw = awc_mm_per_m(idx) * zr
    raw = p * taw
    S = R.shape[0]
    dr = np.zeros(S)                       # root-zone depletion, start at field capacity after sowing rains
    etc_sum, eta_sum, stress_days, irr_sum = np.zeros(S), np.zeros(S), np.zeros(S), np.zeros(S)
    irr_events = [[] for _ in range(S)]
    for j in range(L):
        etc = kc[j] * E[:, j]
        p_eff = np.where(R[:, j] > 25, 25 + 0.8 * (R[:, j] - 25), R[:, j])      # crude runoff on heavy days
        ks = np.where(dr > raw, np.clip((taw - dr) / ((1 - p) * taw), 0, 1), 1.0)
        eta = ks * etc
        dr = np.clip(dr - p_eff + eta, 0, taw)                                    # excess drains (deep percolation)
        if irrigate:
            need = dr > raw
            irr_sum += np.where(need, dr, 0)
            for k in np.where(need)[0]:
                irr_events[k].append((j, float(dr[k])))
            dr = np.where(need, 0.0, dr)
        etc_sum += etc
        eta_sum += eta
        stress_days += ks < 1
    loss = np.clip(ky * (1 - eta_sum / np.maximum(etc_sum, 1e-6)), 0, 1)
    return {"etc": etc_sum, "eta": eta_sum, "loss": loss, "stress_days": stress_days, "irrigation_mm": irr_sum,
            "irr_events": irr_events, "rain": R.sum(axis=1), "length": L, "scenarios": scen, "taw": taw}


def _pct(v, q):
    return round(float(np.percentile(v, q)), 1)


def crop_outlook(idx: int, as_of: dt.date) -> dict:
    """Rank this season's crops by rainfed yield risk; water need and irrigation requirement per crop."""
    season, sow = season_for(as_of)
    rows = []
    for crop, spec in CROPS.items():
        if season not in spec[7]:
            continue
        wb = water_balance(idx, crop, sow, as_of)
        wi = water_balance(idx, crop, sow, as_of, irrigate=True)
        loss = wb["loss"] * 100
        rows.append({
            "crop": crop, "kn": spec[8], "days": wb["length"],
            "water_need_mm": round(float(np.median(wb["etc"]))),
            "rain_mm": round(float(np.median(wb["rain"]))),
            "yield_loss_rainfed_pct": {"p10": _pct(loss, 10), "p50": _pct(loss, 50), "p90": _pct(loss, 90)},
            "stress_days": round(float(np.median(wb["stress_days"]))),
            "irrigation_need_mm": round(float(np.median(wi["irrigation_mm"]))),
        })
    for r in rows:
        l50, l90 = r["yield_loss_rainfed_pct"]["p50"], r["yield_loss_rainfed_pct"]["p90"]
        r["verdict"] = ("good rainfed" if l90 < 20 else "ok rainfed, risky in a dry year" if l50 < 20
                        else "needs irrigation" if l50 < 50 else "avoid without assured irrigation")
    rows.sort(key=lambda r: (r["yield_loss_rainfed_pct"]["p50"] + 0.5 * r["yield_loss_rainfed_pct"]["p90"],
                             r["water_need_mm"]))
    return {"season": season, "sowing_date": sow.isoformat(), "crops": rows,
            "scenarios": len(water_balance(idx, rows[0]["crop"], sow, as_of)["scenarios"]) if rows else 0}


def irrigation_schedule(idx: int, crop: str, as_of: dt.date) -> dict:
    """Irrigation dates and amounts that keep the crop out of water stress, for the median-rain scenario."""
    season, sow = season_for(as_of)
    wi = water_balance(idx, crop, sow, as_of, irrigate=True)
    k = int(np.argsort(wi["rain"])[len(wi["rain"]) // 2])            # median-rain scenario
    events = [{"date": (sow + dt.timedelta(days=j)).isoformat(), "mm": round(mm)} for j, mm in wi["irr_events"][k]]
    upcoming = [e for e in events if e["date"] >= as_of.isoformat()]
    return {"crop": crop, "season": season, "sowing_date": sow.isoformat(), "events": events,
            "next": upcoming[0] if upcoming else None, "total_mm": round(sum(e["mm"] for e in events)),
            "litres_per_acre": round(sum(e["mm"] for e in events) * 4046.86),
            "note": "median-rain scenario; refill the root zone to field capacity when depletion passes the crop's limit"}


def sowing_planner(idx: int, crop: str, as_of: dt.date, weeks: int = 8) -> list[dict]:
    """Rainfed yield-loss risk for sowing in each of the next `weeks` weeks (past-years rain as futures)."""
    season, sow0 = season_for(as_of)
    start = max(sow0 - dt.timedelta(days=21), as_of)
    out = []
    for w in range(weeks):
        sow = start + dt.timedelta(days=7 * w)
        wb = water_balance(idx, crop, sow, as_of)
        loss = wb["loss"] * 100
        out.append({"sowing_date": sow.isoformat(), "loss_p50": _pct(loss, 50), "loss_p90": _pct(loss, 90),
                    "p_loss_over_30": round(float(np.mean(loss > 30)), 2)})
    return out
