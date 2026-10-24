"""THE taluk-risk contract every platform uses. Owner: P1 (core/ML).

Platforms call `taluk_risk(as_of)` and nothing else for risk. Inside: M2 (groundwater forecast, core/gwmodel.py) where
the model file exists and the taluk has monitoring wells; otherwise the provisional index (rain + groundwater anomaly).
The returned keys and shapes never change; fields a model doesn't provide are None.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

from . import gwmodel
from .indicators import provisional_risk, taluk_indicators

DRIVER_LABELS = gwmodel.DRIVER_LABELS


@lru_cache(maxsize=32)
def taluk_risk(as_of: str) -> dict:
    """Per-taluk risk on `as_of` (arrays/lists indexed by taluk idx, length 227).

    Returns:
      model         str               "m2-wells-v2" (ML) or "provisional-index" (no model file)
      source        list[str]         per taluk: "m2" or "provisional" (taluks without wells)
      levels        list[str]         "critical" | "high" | "medium" | "low"
      score         np.ndarray        stress 0..1 (higher = worse)
      drought_prob  np.ndarray | None M1 probability of agricultural drought (None until M1 has real labels)
      days_low/mid/high np.ndarray | None  days until groundwater stress (pessimistic / middle / optimistic);
                                     0 = already at stress, 366 = not within the 6-month forecast horizon
      drivers       list[list[dict]] | None  per taluk: [{"key", "label", "metres"}], most important first
                                     (metres = how much deeper groundwater will be in 3 months because of that factor)
    """
    ind = taluk_indicators(as_of)
    p_score, p_levels = provisional_risk(ind)
    m2 = gwmodel.predict(as_of)
    if m2 is None:
        return {"model": "provisional-index", "source": ["provisional"] * len(p_levels), "levels": p_levels,
                "score": p_score, "drought_prob": None, "days_low": None, "days_mid": None, "days_high": None,
                "drivers": None}

    mid, lo = m2["days_mid"], m2["days_low"]
    has = np.isfinite(mid)
    levels = [m2["levels"][i] if has[i] else p_levels[i] for i in range(len(mid))]
    # score 0..1: 1 = at stress now; pessimistic and middle paths both count
    score = np.where(has, 1 - (0.6 * np.nan_to_num(mid) + 0.4 * np.nan_to_num(lo)) / 366, p_score)
    drivers = []
    for i in range(len(mid)):
        if not has[i]:
            drivers.append([])
            continue
        row = [{"key": k, "label": DRIVER_LABELS[k], "metres": round(float(v[i]), 2)}
               for k, v in m2["drivers_m"].items() if np.isfinite(v[i])]
        drivers.append(sorted(row, key=lambda r: -r["metres"]))
    card = gwmodel.card() or {}
    return {"model": card.get("version", "m2"), "source": ["m2" if h else "provisional" for h in has],
            "levels": levels, "score": score, "drought_prob": None,
            "days_low": m2["days_low"], "days_mid": mid, "days_high": m2["days_high"], "drivers": drivers,
            "gw_threshold_m": m2["threshold_m"], "gw_anom_now_m": m2["anom_now"], "gw_paths": m2["paths"],
            "origin_month": m2["origin_month"]}
