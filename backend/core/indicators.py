"""Shared per-taluk indicators computed from real data (rain, ET0, groundwater wells).

`provisional_risk` is a transparent stand-in until the ML models (PLAN.md §5, M1/M2) are trained.
Every response that uses it says `"model": "provisional-index"` so the UI can label it.
"""
from __future__ import annotations

import datetime as dt
from functools import lru_cache

import numpy as np

from .data import climate, groundwater

RISK_LEVELS = ("low", "medium", "high", "critical")


def rain_deviation(t0: int, days: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Rain over the `days` up to index t0 vs the same calendar window in normal years. Returns
    (observed mm, normal mm, deviation %) per taluk."""
    c = climate()
    lo = max(t0 - days + 1, 0)
    obs = c.rain[lo: t0 + 1].sum(axis=0)
    doys = [dt.date.fromisoformat(c.dates[k]).timetuple().tm_yday - 1 for k in range(lo, t0 + 1)]
    normal = c.rain_doy_normal[doys].sum(axis=0)
    dev = np.where(normal > 1, (obs / np.maximum(normal, 1) - 1) * 100, 0.0)
    return obs, normal, dev


@lru_cache(maxsize=32)
def taluk_indicators(as_of: str) -> dict[str, np.ndarray]:
    c = climate()
    t0 = c.index(as_of)
    r90, n90, d90 = rain_deviation(t0, 90)
    r365, n365, d365 = rain_deviation(t0, 365)
    et0_30 = c.et0[max(t0 - 29, 0): t0 + 1].sum(axis=0)
    depth, anom, month = groundwater().latest(as_of)
    return {"rain_90d_mm": r90, "rain_90d_dev_pct": d90, "rain_365d_mm": r365, "rain_365d_normal_mm": n365,
            "rain_365d_dev_pct": d365, "et0_30d_mm": et0_30, "gw_depth_m": depth, "gw_anom_m": anom, "gw_month": month}


def provisional_risk(ind: dict[str, np.ndarray]) -> tuple[np.ndarray, list[str]]:
    """Stress score 0..1 = mean of: 12-month rain deficit, 3-month rain deficit, groundwater deeper than normal."""
    rain12 = np.clip(-ind["rain_365d_dev_pct"] / 40, 0, 1)
    rain3 = np.clip(-ind["rain_90d_dev_pct"] / 60, 0, 1)
    gw = np.clip(np.nan_to_num(ind["gw_anom_m"], nan=0.0) / 4, 0, 1)
    score = 0.35 * rain12 + 0.25 * rain3 + 0.40 * gw
    levels = [RISK_LEVELS[min(int(s / 0.25), 3)] for s in score]
    return score, levels


def clean(v):
    """numpy -> JSON-safe python (NaN -> None)."""
    if isinstance(v, (np.floating, float)):
        return None if np.isnan(v) else round(float(v), 2)
    if isinstance(v, np.integer):
        return int(v)
    return v
