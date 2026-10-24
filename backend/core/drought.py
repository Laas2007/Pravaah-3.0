"""M1 — agricultural (kharif) drought: labels from the GoI Drought Manual criteria + an early-warning classifier.

Labels (per taluk and kharif season, Jun 1 - Sep 30), following the indicator logic of the Manual for Drought Management
(GoI 2016, updated 2020) that the Karnataka 2023 drought order itself cites, using the real data we have:
  trigger (mandatory): seasonal rainfall deviation <= -20 %   OR   a dry spell of >= 21 consecutive days with < 2.5 mm
                        between 15 Jun and 30 Sep (IMD daily rain)
  impact indicators, points: rainfall severity SPI (season z-score) <= -1.0: 1, <= -1.5: 2
                             moisture adequacy MAI = AET/PET from an FAO-56 root-zone balance: <= 75 %: 1, <= 50 %: 2
                             (the Manual's MAI bands: 51-75 mild, 26-50 moderate, 0-25 severe; our bucket's MAI runs
                             high, and officially severe 2023 taluks sit at a median of 73 %, so the mild band counts.
                             This choice was made after looking at 2023 -> 2023 agreement is in-sample)
                             groundwater at the end of September (wells): >= 1 m deeper than normal: 1, at stress: 2
  label: no trigger -> 0 (no drought); trigger and >= 3 points -> 2 (severe); trigger and >= 1 point -> 1 (moderate)
Not available to us (so not used): satellite vegetation indices (NDVI/VCI) and crop-sown-area data.
The labels are checked against the official 2023 declarations (GO RD 449 TNR 2023) in train/train_drought.py.

Model: gradient-boosted classifier that, from data available on a mid-season date (Jul 1 .. Sep 15), predicts the
end-of-season label -> P(drought) and P(severe), with counterfactual drivers.
"""
from __future__ import annotations

import datetime as dt
import json
from functools import lru_cache
from pathlib import Path

import numpy as np

from .data import climate, regions
from . import gwmodel

MODELS = Path(__file__).resolve().parent.parent / "models"
MODEL_FILE = MODELS / "drought_m1.joblib"
CARD_FILE = MODELS / "drought_m1_card.json"
LABELS_FILE = Path(__file__).resolve().parent.parent / "data" / "karnataka" / "drought_labels.json"
YEARS = range(2015, 2027)
ORIGINS = ((7, 1), (7, 15), (8, 1), (8, 15), (9, 1), (9, 15))
FEATURES = ["rain_dev_season", "rain_dev_30", "rain_dev_60", "dry_spell_now", "longest_dry_spell", "spi_to_date",
            "mai_to_date", "gw_anom", "et0_dev_30", "rain_dev_prev_year", "awc", "normal_season_rain",
            "days_left", "share_normal_left"]
DRIVERS = {
    "rain_deficit": (["rain_dev_season", "rain_dev_30", "rain_dev_60", "spi_to_date"],
                     "Rain this season below normal", "ಈ ಋತುವಿನ ಮಳೆ ವಾಡಿಕೆಗಿಂತ ಕಡಿಮೆ"),
    "dry_spells": (["dry_spell_now", "longest_dry_spell"], "Long dry spells", "ದೀರ್ಘ ಒಣ ಅವಧಿಗಳು"),
    "soil_moisture": (["mai_to_date"], "Low soil moisture for crops", "ಬೆಳೆಗಳಿಗೆ ಮಣ್ಣಿನ ತೇವಾಂಶ ಕಡಿಮೆ"),
    "groundwater": (["gw_anom"], "Groundwater deeper than normal", "ಅಂತರ್ಜಲ ವಾಡಿಕೆಗಿಂತ ಆಳ"),
    "heat": (["et0_dev_30"], "Hot, dry air (high evaporation)", "ಬಿಸಿ, ಒಣ ಗಾಳಿ (ಹೆಚ್ಚು ಆವಿಯಾಗುವಿಕೆ)"),
}


@lru_cache(maxsize=1)
def _base():
    c = climate()
    d0 = dt.date.fromisoformat(c.dates[0])
    doy = np.array([(d0 + dt.timedelta(days=k)).timetuple().tm_yday - 1 for k in range(len(c.dates))])
    yr = np.array([int(x[:4]) for x in c.dates])
    base = (yr >= 2014) & (yr <= 2022)
    et0n = np.stack([c.et0[base & (doy == k)].mean(0) if (base & (doy == k)).any() else c.et0[base].mean(0)
                     for k in range(366)])
    awc = np.array([170.0 if r["lat"] > 15.0 else 110.0 for r in regions()])       # estimated, as in M3
    return c, d0, doy, et0n, awc


def _idx(d: dt.date) -> int:
    c, d0, *_ = _base()
    return int(np.clip((d - d0).days, 0, len(c.dates) - 1))


def _normal(a, b, field="rain"):
    """Normal sum per taluk over climate indices [a, b]."""
    c, _, doy, et0n, _ = _base()
    tab = c.rain_doy_normal if field == "rain" else et0n
    return tab[doy[a:b + 1]].sum(axis=0)


def _longest_run(dry: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """dry: (days, taluks) bool -> (longest run, current run at the end) per taluk."""
    run = np.zeros(dry.shape[1])
    best = np.zeros(dry.shape[1])
    for row in dry:
        run = np.where(row, run + 1, 0)
        best = np.maximum(best, run)
    return best, run


def _mai(a, b):
    """Moisture adequacy (AET / PET) over [a, b] from a 1 m root-zone FAO-56 bucket under a reference crop."""
    c, _, _, _, awc = _base()
    taw = awc * 1.0
    raw = 0.5 * taw
    dr = np.zeros(c.rain.shape[1])
    aet = np.zeros_like(dr)
    pet = np.zeros_like(dr)
    for t in range(a, b + 1):
        et0 = c.et0[t]
        ks = np.where(dr > raw, np.clip((taw - dr) / (taw - raw), 0, 1), 1.0)
        e = ks * et0
        dr = np.clip(dr - c.rain[t] + e, 0, taw)
        aet += e
        pet += et0
    return aet / np.maximum(pet, 1e-6)


def _gw_anom(month: str) -> np.ndarray:
    m = gwmodel.taluk_anom_matrix()
    months = gwmodel.arrays()["months"]
    if month not in months:
        return np.full(m.shape[1], np.nan)
    k = months.index(month)
    out = m[k].copy()
    for back in (1, 2):                      # fall back to a slightly older reading
        if k - back >= 0:
            gap = np.isnan(out)
            out[gap] = m[k - back][gap]
    return out


@lru_cache(maxsize=1)
def season_stats():
    """Per kharif season (2015..): season rain deviation, z-score, longest dry spell, MAI, end-Sep groundwater."""
    c, *_ = _base()
    out = {}
    totals = {}
    for y in YEARS:
        a, b = _idx(dt.date(y, 6, 1)), _idx(dt.date(y, 9, 30))
        if dt.date(y, 9, 30).isoformat() > c.dates[-1]:
            continue
        rain = c.rain[a:b + 1].sum(axis=0)
        totals[y] = rain
        s15 = _idx(dt.date(y, 6, 15))
        longest, _ = _longest_run(c.rain[s15:b + 1] < 2.5)
        out[y] = {"rain": rain, "dev": (rain / np.maximum(_normal(a, b), 1) - 1) * 100, "dry": longest,
                  "mai": _mai(a, b), "gw": _gw_anom(f"{y}-09")}
    R = np.stack(list(totals.values()))
    mu, sd = R.mean(axis=0), R.std(axis=0) + 1e-6
    for y in out:
        out[y]["spi"] = (out[y]["rain"] - mu) / sd
    return out


def label_seasons() -> dict:
    """Drought Manual labels {year: array(taluks) of 0/1/2} + the indicator values behind them."""
    thr = gwmodel.arrays()["thr"]
    labels = {}
    for y, s in season_stats().items():
        trigger = (s["dev"] <= -20) | (s["dry"] >= 21)
        pts = (np.where(s["spi"] <= -1.5, 2, np.where(s["spi"] <= -1.0, 1, 0))
               + np.where(s["mai"] <= 0.50, 2, np.where(s["mai"] <= 0.75, 1, 0))
               + np.where(np.nan_to_num(s["gw"], nan=-99) >= thr, 2, np.where(np.nan_to_num(s["gw"], nan=-99) >= 1.0, 1, 0)))
        lab = np.where(~trigger, 0, np.where(pts >= 3, 2, np.where(pts >= 1, 1, 0)))
        labels[y] = {"label": lab, "trigger": trigger, "points": pts}
    return labels


def features_at(d: dt.date) -> np.ndarray:
    """Feature matrix (taluks x FEATURES) using only data available on date d (mid-kharif)."""
    c, _, _, et0n, awc = _base()
    y = d.year
    a, t = _idx(dt.date(y, 6, 1)), _idx(d)
    end = _idx(dt.date(y, 9, 30))
    rain_to = c.rain[a:t + 1].sum(axis=0)
    dev = lambda lo: (c.rain[lo:t + 1].sum(axis=0) / np.maximum(_normal(lo, t), 1) - 1) * 100
    s15 = _idx(dt.date(y, 6, 15))
    longest, now = _longest_run(c.rain[min(s15, t):t + 1] < 2.5)
    stats = season_stats()
    prev = stats.get(y - 1)
    # season z-score so far, against the same window in earlier years only (no look-ahead)
    hist = []
    for yy in range(2014, y):
        aa, tt = _idx(dt.date(yy, 6, 1)), _idx(dt.date(yy, d.month, d.day))
        hist.append(c.rain[aa:tt + 1].sum(axis=0))
    H = np.stack(hist) if len(hist) >= 2 else np.stack([rain_to, rain_to])
    spi = (rain_to - H.mean(axis=0)) / (H.std(axis=0) + 1e-6)
    gw_month = (d.replace(day=1) - dt.timedelta(days=1)).strftime("%Y-%m")
    et0_30 = c.et0[t - 29:t + 1].sum(axis=0) / np.maximum(et0n[_base()[2][t - 29:t + 1]].sum(axis=0), 1e-6) * 100 - 100
    normal_season = _normal(a, end)
    normal_left = _normal(t + 1, end) if t < end else np.zeros_like(normal_season)
    cols = {
        "rain_dev_season": (rain_to / np.maximum(_normal(a, t), 1) - 1) * 100, "rain_dev_30": dev(t - 29),
        "rain_dev_60": dev(t - 59), "dry_spell_now": now, "longest_dry_spell": longest, "spi_to_date": spi,
        "mai_to_date": _mai(a, t), "gw_anom": _gw_anom(gw_month), "et0_dev_30": et0_30,
        "rain_dev_prev_year": prev["dev"] if prev else np.zeros(len(awc)), "awc": awc,
        "normal_season_rain": normal_season, "days_left": np.full(len(awc), float(max(end - t, 0))),
        "share_normal_left": normal_left / np.maximum(normal_season, 1),
    }
    return np.column_stack([np.asarray(cols[f], dtype=float) for f in FEATURES])


@lru_cache(maxsize=1)
def load():
    if not MODEL_FILE.exists():
        return None
    import joblib
    return joblib.load(MODEL_FILE)


def card() -> dict | None:
    return json.loads(CARD_FILE.read_text()) if CARD_FILE.exists() else None


def kharif_date(as_of: str) -> dt.date | None:
    """The mid-kharif date to forecast from: as_of itself in Jul 1 - Sep 30, else None (outside the season)."""
    d = dt.date.fromisoformat(as_of)
    if (d.month, d.day) < (7, 1) or d.month > 9:
        return None
    return d


# The classifier uses only in-season (dynamic) features, each constrained to push risk in the physical direction
# (more deficit / longer dry spells / drier soil / deeper groundwater can only raise drought risk). Static descriptors
# (soil class, normal rain, last year's rain) let a first version memorise "where droughts happened" and were dropped.
MODEL_FEATURES = ["rain_dev_season", "rain_dev_30", "rain_dev_60", "dry_spell_now", "longest_dry_spell", "spi_to_date",
                  "mai_to_date", "gw_anom", "et0_dev_30", "days_left", "share_normal_left"]
MONOTONIC = [-1, -1, -1, 1, 1, -1, -1, 1, 1, 0, 0]
TRIGGER = "rainfall so far <= -20 % of normal, or a dry spell of >= 21 days (Drought Manual mandatory trigger)"


def _cols():
    return [FEATURES.index(f) for f in MODEL_FEATURES]


def trigger_so_far(X: np.ndarray) -> np.ndarray:
    return (X[:, FEATURES.index("rain_dev_season")] <= -20) | (X[:, FEATURES.index("longest_dry_spell")] >= 21)


def level(trig: np.ndarray, p: np.ndarray, cut: float) -> list[str]:
    """drought likely = trigger met and model probability >= cut; watch = trigger met; else low."""
    return ["likely" if t and q >= cut else "watch" if t else "low" for t, q in zip(trig, p)]


@lru_cache(maxsize=64)
def predict(as_of: str) -> dict | None:
    """Kharif drought early warning from data up to as_of (Jul 1 - Sep 30 only): trigger so far, P(drought by the end
    of the season), level (likely / watch / low) and counterfactual drivers (change in probability)."""
    model = load()
    d = kharif_date(as_of)
    if model is None or d is None:
        return None
    X = features_at(d)
    Xm = X[:, _cols()]
    p = model.predict_proba(Xm)[:, 1]
    trig = trigger_so_far(X)
    drivers = {}
    for key, (cols, *_l) in DRIVERS.items():
        X2 = Xm.copy()
        for col in cols:
            j = MODEL_FEATURES.index(col)
            X2[:, j] = model.medians[j]                          # typical no-drought value from training
        drivers[key] = p - model.predict_proba(X2)[:, 1]       # + = this factor raises the drought probability
    return {"as_of": d.isoformat(), "p_drought": p, "trigger": trig, "level": level(trig, p, model.cut),
            "cut": model.cut, "drivers": drivers,
            "rain_dev_season": X[:, FEATURES.index("rain_dev_season")],
            "longest_dry_spell": X[:, FEATURES.index("longest_dry_spell")],
            "mai_to_date": X[:, FEATURES.index("mai_to_date")]}
