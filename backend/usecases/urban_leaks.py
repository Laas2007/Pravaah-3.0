"""M6 — leak and abnormal-use detection for water meters (owner: P3).

No public household meter data exists in India, so the detector is demonstrated on SYNTHETIC hourly meter data with
planted leaks and planted heavy-use days (and the truth known), and it can be run on any uploaded meter CSV.
  leak rule      : a leak shows as water still flowing at night. Night minimum (lowest hourly flow 01:00-04:59)
                   >= max(4 L/h, the meter's own first-week night baseline + 4 L/h) on 3+ nights in a row.
  abnormal days  : IsolationForest on daily features (total, night minimum, peak hour, morning share), learned per
                   batch of meters; flags unusual heavy-use days (garden watering, tank overflow, guests ...).
"""
from __future__ import annotations

import csv
import io
from functools import lru_cache

import numpy as np
from sklearn.ensemble import IsolationForest

NIGHT = slice(1, 5)          # hours 01:00-04:59
PROFILE = np.array([0.5, 0.2, 0.1, 0.1, 0.2, 1.5, 6.0, 9.0, 8.0, 5.0, 3.5, 3.0, 3.5, 3.0, 2.5, 2.5, 3.0, 4.5,
                    7.0, 8.0, 6.5, 4.5, 2.5, 1.2])
PROFILE = PROFILE / PROFILE.sum()


def synth(n_meters=120, days=56, n_leaks=20, seed=7):
    """Hourly litres (meters x days x 24) with planted leaks and heavy-use events. Returns (data, truth).

    Deliberately hard: many Bengaluru homes fill their sump from the municipal supply at night (alternate days for
    most, every night for some), which looks like night flow without being a leak; and some leaks are tiny drips."""
    rng = np.random.default_rng(seed)
    data = np.zeros((n_meters, days, 24))
    truth = {"leak_start": {}, "leak_rate": {}, "heavy_days": set()}
    leakers = rng.choice(n_meters, n_leaks, replace=False)
    fill = rng.choice(["none", "alternate", "nightly"], n_meters, p=[0.65, 0.27, 0.08])
    for m in range(n_meters):
        people = rng.integers(2, 7)
        for d in range(days):
            if fill[m] == "nightly" or (fill[m] == "alternate" and d % 2 == m % 2):
                h0 = int(rng.integers(0, 3))
                data[m, d, h0:h0 + int(rng.integers(2, 5))] += rng.uniform(20, 80)   # slow sump fill at night
            total = 135 * people * rng.lognormal(0, 0.15) * (1.1 if d % 7 in (5, 6) else 1.0)
            day = total * PROFILE * rng.lognormal(0, 0.35, 24)
            day[NIGHT] += (rng.random(4) < 0.1) * rng.uniform(5, 10, 4)  # occasional night flush (few litres)
            if rng.random() < 0.04:                                    # heavy-use day: watering / tank refill
                h = rng.integers(6, 20)
                day[h:h + 2] += rng.uniform(200, 600)
                truth["heavy_days"].add((m, d))
            data[m, d] += day
        if m in leakers:
            start = int(rng.integers(10, 45))
            rate = float(rng.choice([rng.uniform(2, 4), rng.uniform(5, 10), rng.uniform(15, 40)]))  # drip / tap / toilet
            data[m, start:, :] += rate * rng.lognormal(0, 0.1, (days - start, 24))
            truth["leak_start"][m] = start
            truth["leak_rate"][m] = round(rate, 1)
    return data, truth


def detect_leak(series: np.ndarray):
    """series: days x 24 hourly litres for one meter -> (leak_start_day | None, night_min per day)."""
    night_min = series[:, NIGHT].min(axis=1)
    base = float(np.median(night_min[:7])) if len(night_min) >= 7 else 0.0
    flag = night_min >= max(4.0, base + 4.0)
    run = 0
    for d, f in enumerate(flag):
        run = run + 1 if f else 0
        if run >= 3:
            return d - 2, night_min
    return None, night_min


def daily_features(data):
    tot = data.sum(axis=2)
    return np.stack([tot, data[:, :, NIGHT].min(axis=2), data.argmax(axis=2), data[:, :, 5:10].sum(axis=2) / np.maximum(tot, 1)],
                    axis=2)


@lru_cache(maxsize=1)
def demo() -> dict:
    data, truth = synth()
    n, days, _ = data.shape
    found = {m: detect_leak(data[m])[0] for m in range(n)}
    leakers = set(truth["leak_start"])
    flagged = {m for m, s in found.items() if s is not None}
    tp = flagged & leakers
    delays = [found[m] - truth["leak_start"][m] for m in tp]
    F = daily_features(data).reshape(-1, 4)
    iso = IsolationForest(contamination=0.04, random_state=0).fit(F)
    abn = (iso.predict(F) == -1).reshape(n, days)
    heavy = truth["heavy_days"]
    abn_set = {(m, d) for m, d in zip(*np.where(abn))}
    leak_days = {(m, d) for m, s in truth["leak_start"].items() for d in range(s, days)}
    examples = []
    for m in (sorted(tp)[:1] + [x for x in range(n) if x not in leakers][:1]):
        start, nm = detect_leak(data[m])
        examples.append({"meter": f"M{m:03d}", "leak": m in leakers, "true_start_day": truth["leak_start"].get(m),
                         "detected_day": start, "night_min_lph": [round(float(v), 1) for v in nm],
                         "daily_litres": [round(float(v)) for v in data[m].sum(axis=1)]})
    false_pos = sorted(flagged - leakers)
    return {
        "synthetic": True, "meters": n, "days": days, "planted_leaks": len(leakers),
        "false_alarm_note": "false alarms are homes that fill their sump from the night-time supply every night"
        if false_pos else None,
        "leaks": {"flagged": len(flagged), "correct": len(tp), "precision": round(len(tp) / max(len(flagged), 1), 2),
                  "recall": round(len(tp) / max(len(leakers), 1), 2),
                  "median_delay_days": float(np.median(delays)) if delays else None,
                  "missed_rates_lph": [truth["leak_rate"][m] for m in leakers - tp]},
        "abnormal_days": {"flagged": len(abn_set), "planted_heavy_days": len(heavy),
                          "heavy_days_caught": len(abn_set & heavy),
                          "flags_explained": round(len(abn_set & (heavy | leak_days)) / max(len(abn_set), 1), 2)},
        "examples": examples,
        "flagged_meters": [{"meter": f"M{m:03d}", "detected_day": found[m], "true_leak": m in leakers,
                            "night_min_lph": round(float(detect_leak(data[m])[1][-7:].mean()), 1)} for m in sorted(flagged)],
    }


def check_csv(text: str) -> dict:
    """Uploaded meter readings: CSV with columns timestamp (YYYY-MM-DD HH:MM) and litres (per hour)."""
    rows = list(csv.DictReader(io.StringIO(text.strip())))
    if not rows:
        return {"error": "empty file"}
    keys = {k.lower().strip(): k for k in rows[0]}
    tk = keys.get("timestamp") or keys.get("time") or list(rows[0])[0]
    lk = keys.get("litres") or keys.get("liters") or keys.get("litres_per_hour") or list(rows[0])[1]
    by_day = {}
    for r in rows:
        ts = r[tk].strip()
        day, hour = ts[:10], int(ts[11:13]) if len(ts) >= 13 else 0
        by_day.setdefault(day, np.zeros(24))[hour] += float(r[lk] or 0)
    days = sorted(by_day)
    series = np.stack([by_day[d] for d in days])
    start, nm = detect_leak(series)
    return {"days": len(days), "first_day": days[0], "last_day": days[-1],
            "leak_suspected": start is not None, "leak_from": days[start] if start is not None else None,
            "night_min_lph": [round(float(v), 1) for v in nm], "daily_litres": [round(float(v)) for v in series.sum(axis=1)],
            "dates": days,
            "advice": "Water keeps flowing at night: check toilet flappers, overhead-tank float valves and taps."
            if start is not None else "No night-time flow pattern that suggests a leak."}
