"""Train M2 (well-level groundwater forecast, see backend/core/gwmodel.py) and write its model card.

    python train/train_gw.py            # ~15 min

1. Panel: every well x every month-end origin (2015-01 ..) x horizon 1..6 months, wells with a reading at both ends.
   Target = change in depth to water (m) over the horizon (real NWDP readings). Rain in the window = what really fell.
2. Honest validation with models trained on targets up to 2021-12, tested on origins from 2022-01:
   a. well level: error vs "no change" and "usual seasonal change" baselines;
   b. taluk level through the SAME code the app uses (gwmodel._taluk_paths, past-years rain as futures):
      error, 10-90 % range coverage, and the 2023 event (from Oct 2023 forecast Apr 2024 stress).
3. Final models on all rows -> models/gw_m2.joblib, metrics -> models/gw_m2_card.json.
"""
import datetime as dt
import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import sklearn
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import gwmodel as gm  # noqa: E402

FIRST_ORIGIN = "2015-01"
TRAIN_TARGET_UNTIL = "2021-12"
TEST_ORIGIN_FROM = "2022-01"
EVENT = ("2023-10", 6)             # origin month, horizon -> 2024-04 (Bengaluru crisis peak)
MAX_TRAIN_ROWS = 900_000


def build_panel():
    a = gm.arrays()
    W, months = a["W"], a["months"]
    clim_end = dt.date.fromisoformat(a["c"].dates[-1])
    X, y, meta = [], [], []
    for k, om in enumerate(months):
        if om < FIRST_ORIGIN:
            continue
        if gm.month_end(om) > clim_end:
            break
        has = ~np.isnan(W[:, k])
        for h in gm.HORIZONS:
            if k + h >= len(months):
                break
            wells = np.where(has & ~np.isnan(W[:, k + h]))[0]
            if len(wells) == 0:
                continue
            X.append(gm.well_features(k, h, wells))
            y.append(W[wells, k + h] - W[wells, k])
            meta.append(np.column_stack([np.full(len(wells), k), wells, np.full(len(wells), h)]))
    return np.vstack(X), np.concatenate(y), np.vstack(meta).astype(int)


def fit(X, y, q):
    return HistGradientBoostingRegressor(loss="quantile", quantile=q, max_iter=300, learning_rate=0.06,
                                         max_leaf_nodes=31, min_samples_leaf=200, l2_regularization=1.0,
                                         random_state=0).fit(X, y)


def subsample(idx, n, seed=0):
    return idx if len(idx) <= n else np.random.default_rng(seed).choice(idx, size=n, replace=False)


def taluk_actual(k):
    """Actual taluk anomaly in month k (median over wells with a reading)."""
    a = gm.arrays()
    out = np.full(a["T"], np.nan)
    for t in range(a["T"]):
        v = a["anom"][a["wt"] == t, k]
        v = v[np.isfinite(v)]
        if len(v):
            out[t] = np.median(v)
    return out


def main():
    t0 = time.time()
    a = gm.arrays()
    months = a["months"]
    X, y, meta = build_panel()
    K, J, H = meta.T
    orig = np.array(months)[K]
    targ = np.array(months)[np.minimum(K + H, len(months) - 1)]
    print(f"panel: {len(y):,} rows x {X.shape[1]} features, origins {min(orig)}..{max(orig)} ({time.time() - t0:.0f}s)")

    tr = np.where(targ <= TRAIN_TARGET_UNTIL)[0]
    te = np.where(orig >= TEST_ORIGIN_FROM)[0]
    tri = subsample(tr, MAX_TRAIN_ROWS)
    print(f"validation: train {len(tri):,} rows (targets <= {TRAIN_TARGET_UNTIL}), test {len(te):,} rows")
    vmodels = {q: fit(X[tri], y[tri], q) for q in gm.QUANTILES}

    # a. well level, actual rain (upper bound) vs baselines
    seas = np.nan_to_num(X[te][:, gm.FEATURES.index("seas")], nan=0.0)
    p50 = vmodels[0.5].predict(X[te])
    yt, ht = y[te], H[te]
    mae = lambda p, s: round(float(np.mean(np.abs(yt[s] - p[s]))), 2)
    well = {}
    for h in (1, 3, 6):
        s = ht == h
        well[h] = {"model_actual_rain": mae(p50, s), "no_change": mae(np.zeros_like(yt), s), "seasonal": mae(seas, s)}
    print("well-level MAE of depth change (m), test:", well)

    # b. taluk level through the serving code, quarterly origins in the test period
    origins = [m for m in months if m >= TEST_ORIGIN_FROM and m[5:7] in ("01", "04", "07", "10")
               and months.index(m) + 6 < len(months)]
    errs, errs0, cover, n = [], [], 0, 0
    for om in origins:
        k0 = months.index(om)
        d = gm.month_end(om) + dt.timedelta(days=1)
        paths = gm._taluk_paths(vmodels, k0, d)
        now = gm._now_anom(k0)
        for j, h in enumerate(gm.HORIZONS):
            act = taluk_actual(k0 + h)
            ok = np.isfinite(act) & np.isfinite(paths[50][:, j]) & np.isfinite(now)
            errs.append(np.abs(paths[50][ok, j] - act[ok]))
            errs0.append(np.abs(now[ok] - act[ok]))
            cover += int(np.sum((act[ok] >= paths[10][ok, j]) & (act[ok] <= paths[90][ok, j])))
            n += int(ok.sum())
    taluk = {"origins": len(origins), "pairs": n, "mae_model_m": round(float(np.mean(np.concatenate(errs))), 2),
             "mae_no_change_m": round(float(np.mean(np.concatenate(errs0))), 2), "coverage_10_90": round(cover / n, 2)}
    print("taluk-level (serving code, past-years rain):", taluk)

    # 2023 event
    eo, eh = EVENT
    k0 = months.index(eo)
    paths = gm._taluk_paths(vmodels, k0, gm.month_end(eo) + dt.timedelta(days=1))
    now = gm._now_anom(k0)
    act = taluk_actual(k0 + eh)
    pred = paths[50][:, eh - 1]
    ok = np.isfinite(act) & np.isfinite(pred) & np.isfinite(now)
    thr = a["thr"]
    ah, ph = act[ok] >= thr[ok], pred[ok] >= thr[ok]
    tp = int((ah & ph).sum())
    event = {"origin": eo, "target": months[k0 + eh], "taluks": int(ok.sum()),
             "spearman": round(float(spearmanr(pred[ok], act[ok]).statistic), 2),
             "actual_in_stress": int(ah.sum()), "flagged": int(ph.sum()), "correct": tp,
             "recall": round(tp / max(int(ah.sum()), 1), 2), "precision": round(tp / max(int(ph.sum()), 1), 2),
             "mae_m": round(float(np.mean(np.abs(pred[ok] - act[ok]))), 2),
             "mae_no_change_m": round(float(np.mean(np.abs(now[ok] - act[ok]))), 2)}
    print("2023 event:", event)

    # warning tiers: a tier flags a taluk if its path is at/above stress in the target month
    tiers = {"note": "Validation models (trained on targets <= 2021-12). A tier 'flags' a taluk if that forecast "
                     "path is at/above the stress level in the target month.", "events": []}
    for eo_, eh_ in (("2023-10", 6), ("2023-07", 3)):
        k_ = months.index(eo_)
        pth = gm._taluk_paths(vmodels, k_, gm.month_end(eo_) + dt.timedelta(days=1))
        act_ = taluk_actual(k_ + eh_)
        ok_ = np.isfinite(act_) & np.isfinite(pth[50][:, eh_ - 1])
        ah_ = act_[ok_] >= thr[ok_]
        ev = {"origin": eo_, "target": months[k_ + eh_], "actual_in_stress": int(ah_.sum()), "taluks": int(ok_.sum())}
        for name, p in (("watch_pessimistic", 90), ("warning_likely", 50)):
            ph_ = pth[p][ok_, eh_ - 1] >= thr[ok_]
            tp_ = int((ah_ & ph_).sum())
            ev[name] = {"flagged": int(ph_.sum()), "correct": tp_, "recall": round(tp_ / max(int(ah_.sum()), 1), 2),
                        "precision": round(tp_ / max(int(ph_.sum()), 1), 2)}
        tiers["events"].append(ev)
    print("warning tiers:", tiers["events"])

    # importance: MAE increase when a feature is shuffled (well level, test subsample)
    rng = np.random.default_rng(0)
    sub = subsample(te, 30_000)
    base = np.mean(np.abs(y[sub] - vmodels[0.5].predict(X[sub])))
    imp = {}
    for j, name in enumerate(gm.FEATURES):
        Xp = X[sub].copy()
        Xp[:, j] = rng.permutation(Xp[:, j])
        imp[name] = round(float(np.mean(np.abs(y[sub] - vmodels[0.5].predict(Xp))) - base), 3)
    imp = dict(sorted(imp.items(), key=lambda kv: -kv[1]))
    print("importance:", list(imp.items())[:6])

    print("fitting final models on all rows ...")
    alli = subsample(np.arange(len(y)), MAX_TRAIN_ROWS + 300_000)
    final = {q: fit(X[alli], y[alli], q) for q in gm.QUANTILES}
    gm.MODELS.mkdir(exist_ok=True)
    joblib.dump(final, gm.MODEL_FILE, compress=3)
    card = {
        "model": "M2 groundwater forecast: well-level quantile gradient boosting + past-years rain ensemble",
        "version": "m2-wells-v2", "trained": dt.date.today().isoformat(), "sklearn": sklearn.__version__,
        "label": "Change in depth to water over 1-6 months at 2,664 NWDP monitoring wells (real readings)",
        "features": gm.FEATURES, "quantiles": list(gm.QUANTILES), "rows": int(len(y)),
        "train_rows_used": int(len(alli)), "origins": [str(min(orig)), str(max(orig))],
        "stress_definition": "taluk median well anomaly >= taluk's own 90th percentile of 2014-2021 (>= 1 m deeper than normal)",
        "validation": {"split": f"train targets <= {TRAIN_TARGET_UNTIL}, test origins >= {TEST_ORIGIN_FROM}",
                       "well_level_mae_m": well, "taluk_level": taluk},
        "event_2023": event, "warning_tiers": tiers, "importance": imp,
        "risk_levels": "critical: at stress now or middle path within 90 days; high: middle path within 6 months; "
                       "medium (watch): pessimistic path within 6 months; low: otherwise",
    }
    gm.CARD_FILE.write_text(json.dumps(card, indent=2))
    print(f"saved {gm.MODEL_FILE.name} ({gm.MODEL_FILE.stat().st_size / 1e6:.1f} MB) + card in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
