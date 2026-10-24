"""THE taluk-risk contract every platform uses. Owner: P1 (core/ML).

Platforms call `taluk_risk(as_of)` and nothing else for risk. Today it wraps the provisional index; P1 replaces the
inside with M1 (drought classifier) + M2 (days-to-shortage) WITHOUT changing the returned keys or array shapes.
Fields that a model doesn't provide yet are None.
"""
from __future__ import annotations

from functools import lru_cache

from .indicators import provisional_risk, taluk_indicators


@lru_cache(maxsize=32)
def taluk_risk(as_of: str) -> dict:
    """Per-taluk risk on `as_of` (arrays/lists indexed by taluk idx, length 227).

    Returns:
      model         str               "provisional-index" now; e.g. "m1-gbm-v1+m2-v1" later
      levels        list[str]         "critical" | "high" | "medium" | "low"
      score         np.ndarray        stress 0..1 (higher = worse)
      drought_prob  np.ndarray | None M1 probability of agricultural drought
      days_low/mid/high np.ndarray | None  M2 days until groundwater shortage (25/50/75th pct, 366 = none in a year)
      drivers       list[list[dict]] | None  per taluk: [{"key", "label", "days" or "weight"}] sorted, most important first
    """
    ind = taluk_indicators(as_of)
    score, levels = provisional_risk(ind)
    return {"model": "provisional-index", "levels": levels, "score": score, "drought_prob": None,
            "days_low": None, "days_mid": None, "days_high": None, "drivers": None}
