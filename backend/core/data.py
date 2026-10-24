"""Loaders for the Karnataka base data in data/karnataka/ (built by train/fetch_karnataka.py and train/clean_nwdp.py).

Everything is loaded once and cached. Arrays are indexed [day or month, taluk idx]; taluk idx matches regions.json.
"""
from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from fastapi import HTTPException

KA = Path(__file__).resolve().parent.parent / "data" / "karnataka"
NORMAL_YEARS = (2014, 2022)   # baseline before the 2023 drought (same as the Bengaluru model)


@lru_cache(maxsize=1)
def regions() -> list[dict]:
    return json.loads((KA / "regions.json").read_text(encoding="utf-8"))["taluks"]


@lru_cache(maxsize=4)
def geojson_bytes(name: str) -> bytes:
    """'taluks' or 'districts' (already simplified + rounded by the fetch script)."""
    return (KA / f"{name}.geojson").read_bytes()


@dataclass
class Climate:
    dates: list[str]
    rain: np.ndarray        # mm/day (IMD gauge grid; bias-corrected ERA5 after IMD's last year)
    et0: np.ndarray         # mm/day, FAO Penman-Monteith (ERA5)
    tmax: np.ndarray
    tmin: np.ndarray
    imd_until: str
    rain_doy_normal: np.ndarray   # (366, taluks) mean rain per calendar day over NORMAL_YEARS

    def index(self, as_of: str) -> int:
        d0 = dt.date.fromisoformat(self.dates[0])
        i = (dt.date.fromisoformat(as_of) - d0).days
        return int(np.clip(i, 0, len(self.dates) - 1))


@lru_cache(maxsize=1)
def climate() -> Climate:
    z = np.load(KA / "climate.npz")
    dates = [str(d) for d in z["dates"]]
    rain = z["rain"]
    doy = np.array([dt.date.fromisoformat(d).timetuple().tm_yday - 1 for d in dates])
    yr = np.array([int(d[:4]) for d in dates])
    base = (yr >= NORMAL_YEARS[0]) & (yr <= NORMAL_YEARS[1])
    normal = np.stack([rain[base & (doy == k)].mean(axis=0) if (base & (doy == k)).any() else np.zeros(rain.shape[1])
                       for k in range(366)])
    return Climate(dates, rain, z["et0"], z["tmax"], z["tmin"], str(z["rain_source_imd_until"]), normal)


@dataclass
class Groundwater:
    months: list[str]       # 'YYYY-MM'
    depth: np.ndarray       # median depth to water, m below ground (NaN = no reading)
    anom: np.ndarray        # median anomaly vs each well's 2014-2022 month normal, m (+ = deeper = worse)
    wells: np.ndarray       # wells reporting

    def latest(self, as_of: str, idx: int | None = None, max_age: int = 6):
        """Most recent monthly value from a month that had fully ended before as_of (at most max_age months old).

        Readings are stamped with their month (01-MM), so the as_of month itself may not be known yet: no look-ahead.
        Months that only a few taluks have reported yet are skipped (see usable_month)."""
        last = self.usable_month(last_complete_month(as_of))
        m = self.months.index(last) if last in self.months else (len(self.months) - 1 if last > self.months[-1] else -1)
        if m < 0:
            nan = np.full(self.depth.shape[1], np.nan, dtype=np.float32)
            return (nan[idx], nan[idx], "") if idx is not None else (nan, nan.copy(), np.full(len(nan), "", dtype=object))
        depth = np.full(self.depth.shape[1], np.nan, dtype=np.float32)
        anom = depth.copy()
        month = np.full(self.depth.shape[1], "", dtype=object)
        for k in range(m, max(m - max_age, -1), -1):
            fill = np.isnan(depth) & ~np.isnan(self.depth[k])
            depth[fill], anom[fill], month[fill] = self.depth[k][fill], self.anom[k][fill], self.months[k]
        if idx is not None:
            return depth[idx], anom[idx], month[idx]
        return depth, anom, month


    def usable_month(self, last: str, share: float = 0.5, max_back: int = 3) -> str:
        """Latest month <= last that most taluks have reported: readings arrive over several months, so a month with
        fewer than `share` x the usual number of reporting taluks (median of the 12 months before) is skipped."""
        if last not in self.months:
            last = self.months[-1] if last > self.months[-1] else last
            if last not in self.months:
                return last
        k = self.months.index(last)
        rep = (self.wells > 0).sum(axis=1)
        for _ in range(max_back):
            usual = np.median(rep[max(0, k - 12):k]) if k >= 3 else 0
            if k == 0 or rep[k] >= share * usual:
                break
            k -= 1
        return self.months[k]


def last_complete_month(as_of: str) -> str:
    """'YYYY-MM' of the month before as_of's month (the latest month whose readings are fully known on as_of)."""
    d = dt.date.fromisoformat(as_of).replace(day=1) - dt.timedelta(days=1)
    return d.strftime("%Y-%m")


@lru_cache(maxsize=1)
def groundwater() -> Groundwater:
    z = np.load(KA / "gw_taluk.npz")
    return Groundwater([str(m) for m in z["months"]], z["depth"], z["anom"], z["wells"])


@lru_cache(maxsize=1)
def reservoirs() -> list[dict]:
    return json.loads((KA / "reservoirs.json").read_text(encoding="utf-8"))["reservoirs"]


@lru_cache(maxsize=1)
def tanks() -> dict[int, dict]:
    t = json.loads((KA / "tanks_taluk.json").read_text(encoding="utf-8"))["taluks"]
    return {int(k): v for k, v in t.items()}


def clamp_date(as_of: str | None) -> str:
    """Validate an as_of date and clamp it to the climate record (needs one year of history)."""
    c = climate()
    if not as_of:
        return c.dates[-1]
    try:
        d = dt.date.fromisoformat(as_of)
    except ValueError:
        raise HTTPException(400, "date must be YYYY-MM-DD")
    lo = dt.date.fromisoformat(c.dates[0]) + dt.timedelta(days=365)
    return min(max(d, lo), dt.date.fromisoformat(c.dates[-1])).isoformat()


def taluk(idx: int) -> dict:
    r = regions()
    if not 0 <= idx < len(r):
        raise HTTPException(404, "unknown taluk")
    return r[idx]
