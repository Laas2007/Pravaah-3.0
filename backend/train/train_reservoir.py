"""Train M4 (reservoir storage forecast, see backend/core/reservoir_model.py) and write its model card.

    python train/train_reservoir.py          # ~3 min

Rows: 9 dams x weekly origins (2015 ..) x horizons 15..180 days; target = change in storage as a fraction of design
capacity (real NWDP daily records). Validation: train on targets up to 2021-12-31, test on origins from 2022 with
past-years rain as futures (the way the app forecasts), against "no change" and "usual seasonal change" baselines.
Saves models/res_m4_validation.joblib (for honest replays of 2022+ dates), models/res_m4.joblib (all data) and card.
"""
import datetime as dt
import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.ensemble import HistGradientBoostingRegressor

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import reservoir_model as rm  # noqa: E402

STEP = 7


def build():
    a = rm.arrays()
    n = a["n"]
    cut = (dt.date.fromisoformat(rm.TRAIN_UNTIL) - a["d0"]).days
    X, y, meta = [], [], []
    for name in rm.DAMS:
        s = a["dams"][name]["s"]
        for t in range(365, n, STEP):
            for h in rm.HORIZONS:
                if t + h >= n or np.isnan(s[t + h]):
                    continue
                x = rm.features(name, t, h)
                if x is None:
                    continue
                X.append(x)
                y.append(s[t + h] - s[t])
                meta.append((rm.DAMS.index(name), t, h))
    meta = np.array(meta)
    return np.array(X), np.array(y), meta, cut


def fit(X, y, q):
    return HistGradientBoostingRegressor(loss="quantile", quantile=q, max_iter=300, learning_rate=0.05,
                                         max_leaf_nodes=31, min_samples_leaf=40, l2_regularization=1.0,
                                         categorical_features=[0], random_state=0).fit(X, y)


def main():
    t0 = time.time()
    a = rm.arrays()
    X, y, meta, cut = build()
    dam, tt, hh = meta.T
    print(f"rows {len(y):,} ({time.time() - t0:.0f}s)")
    tr = tt + hh <= cut
    te = tt > cut
    vm = {q: fit(X[tr], y[tr], q) for q in rm.QUANTILES}
    print(f"validation models on {tr.sum():,} rows")

    # seasonal baseline: mean change per (dam, origin week-of-year, horizon) in training rows
    wk = a["doy"][tt] // 7
    key = dam * 100000 + wk * 1000 + hh
    clim = {}
    for k, v in zip(key[tr], y[tr]):
        clim.setdefault(k, []).append(v)
    clim = {k: float(np.mean(v)) for k, v in clim.items()}

    # operational test: past-years rain as futures, monthly origins in the test period
    res = {h: {"model": [], "none": [], "seas": [], "cov": []} for h in rm.HORIZONS}
    for name in rm.DAMS:
        s = a["dams"][name]["s"]
        di = rm.DAMS.index(name)
        for t in range(cut + 1, a["n"], 30):
            f = rm.forecast(vm, name, t)
            if f is None:
                continue
            for j, h in enumerate(rm.HORIZONS):
                if t + h >= a["n"] or np.isnan(s[t + h]):
                    continue
                act = s[t + h]
                res[h]["model"].append(abs(f["p50"][j] - act))
                res[h]["none"].append(abs(s[t] - act))
                res[h]["seas"].append(abs(s[t] + clim.get(di * 100000 + (a["doy"][t] // 7) * 1000 + h, 0.0) - act))
                res[h]["cov"].append(f["p10"][j] <= act <= f["p90"][j])
    table = {h: {"model_pct_cap": round(100 * float(np.mean(v["model"])), 1),
                 "no_change_pct_cap": round(100 * float(np.mean(v["none"])), 1),
                 "seasonal_pct_cap": round(100 * float(np.mean(v["seas"])), 1),
                 "coverage_10_90": round(float(np.mean(v["cov"])), 2), "n": len(v["model"])}
             for h, v in res.items() if v["model"]}
    print("\nTEST (2022+, past-years rain), mean abs error in % of capacity")
    print(f"  {'h':>4} {'model':>6} {'no-chg':>7} {'season':>7} {'cover':>6}   n")
    for h, r in table.items():
        print(f"  {h:>4} {r['model_pct_cap']:>6} {r['no_change_pct_cap']:>7} {r['seasonal_pct_cap']:>7} {r['coverage_10_90']:>6}   {r['n']}")

    # event: KRS during the 2023 Cauvery crisis
    krs = a["dams"]["K.R.Sagara Dam"]
    event = []
    for start in ("2023-06-01", "2023-08-01", "2023-10-01"):
        t = (dt.date.fromisoformat(start) - a["d0"]).days
        f = rm.forecast(vm, "K.R.Sagara Dam", t)
        row = {"origin": start, "storage_now_tmc": round(krs["s"][t] * krs["cap"], 1), "points": []}
        for j, h in enumerate(rm.HORIZONS):
            if t + h < a["n"] and not np.isnan(krs["s"][t + h]):
                row["points"].append({"days": h, "actual_tmc": round(krs["s"][t + h] * krs["cap"], 1),
                                      "p10_tmc": round(f["p10"][j] * krs["cap"], 1),
                                      "p50_tmc": round(f["p50"][j] * krs["cap"], 1),
                                      "p90_tmc": round(f["p90"][j] * krs["cap"], 1)})
        event.append(row)
        print(f"\nKRS from {start} ({row['storage_now_tmc']} TMC):",
              [(p["days"], p["actual_tmc"], f"{p['p10_tmc']}-{p['p90_tmc']}") for p in row["points"]])

    rm.MODELS.mkdir(exist_ok=True)
    joblib.dump(vm, rm.VALID_FILE, compress=3)
    final = {q: fit(X, y, q) for q in rm.QUANTILES}
    joblib.dump(final, rm.MODEL_FILE, compress=3)
    card = {"model": "M4 reservoir storage forecast (quantile gradient boosting + past-years catchment rain)",
            "version": "m4-v1", "trained": dt.date.today().isoformat(), "sklearn": sklearn.__version__,
            "dams": rm.DAMS, "catchment_taluks": rm.CATCHMENT, "features": rm.FEATURES, "rows": int(len(y)),
            "label": "Change in gross storage (fraction of design capacity) over 15-180 days, NWDP daily records",
            "validation": {"split": f"train targets <= {rm.TRAIN_UNTIL}, test origins after", "by_horizon": table},
            "event_krs_2023": event, "low_threshold": f"{int(rm.LOW_FRAC * 100)}% of design capacity"}
    rm.CARD_FILE.write_text(json.dumps(card, indent=2))
    print(f"\nsaved models + card in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
