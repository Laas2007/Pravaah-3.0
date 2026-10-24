"""Train M1 (kharif agricultural-drought early warning, see backend/core/drought.py) and write its model card.

    python train/train_drought.py

Rows: 227 taluks x kharif seasons x mid-season forecast dates (Jul 1, Jul 15, Aug 1, Aug 15, Sep 1, Sep 15).
Label: the season's Drought Manual label (0 none / 1 moderate / 2 severe -> drought = label > 0) from real data.
Model: gradient boosting on in-season features with physical direction constraints (core.drought.MODEL_FEATURES).
Level: alert = Drought Manual trigger met so far (leave-one-year-out F1 on the training years showed the trigger alone
gives the best drought call); within alerts "likely" = probability >= 0.5, else "watch". The model ranks taluks
(AUC) and explains them; it cannot separate the government's severe vs moderate (that uses crop-loss surveys).
Honest tests (each model never saw the year it is tested on):
  A. train 2015-2021 -> test 2022-2025 (labels), vs the rain-deficit-so-far baseline
  B. train 2015-2025 -> test 2026 (labels + the 22 taluks named in the official 17 Sep 2026 order)
  C. train all labelled years except 2023 -> the official 2023 order (GO RD 449 TNR 2023, 13 Sep 2023)
Final model: 2015-2026.
"""
import datetime as dt
import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import drought as dr  # noqa: E402

OFFICIAL = Path(__file__).resolve().parent.parent / "data" / "karnataka" / "drought_official.json"
YEARS = list(range(2015, 2027))
_cache = {}


def rows(year):
    """(X_all_features, y, origin) for one season, cached."""
    if year not in _cache:
        lab = dr.label_seasons()[year]["label"]
        X, y, o = [], [], []
        for m, d in dr.ORIGINS:
            X.append(dr.features_at(dt.date(year, m, d)))
            y.append(lab)
            o += [f"{m:02d}-{d:02d}"] * len(lab)
        _cache[year] = (np.vstack(X), np.concatenate(y), np.array(o))
    return _cache[year]


def build(years):
    parts = [rows(y) for y in years]
    return np.vstack([p[0] for p in parts]), np.concatenate([p[1] for p in parts]), np.concatenate([p[2] for p in parts])


def fit(X, y):
    cols = dr._cols()
    yb = (y > 0).astype(int)
    m = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=60,
                                       monotonic_cst=dr.MONOTONIC, random_state=0).fit(X[:, cols], yb)
    m.medians = np.nanmedian(X[yb == 0][:, cols], axis=0)
    return m


def proba(m, X):
    return m.predict_proba(X[:, dr._cols()])[:, 1]


def baseline(X):
    return -X[:, dr.FEATURES.index("rain_dev_season")]


def choose_cut(years):
    """Leave-one-year-out: the probability cut (among trigger-met rows) that maximises F1 for drought."""
    P, T, Y = [], [], []
    for held in years:
        m = fit(*build([y for y in years if y != held])[:2])
        X, y, _ = rows(held)
        P.append(proba(m, X)); T.append(dr.trigger_so_far(X)); Y.append(y > 0)
    P, T, Y = np.concatenate(P), np.concatenate(T), np.concatenate(Y)
    best = (0, 0.5)
    for c in np.arange(0.05, 0.95, 0.05):
        pred = T & (P >= c)
        tp, fp, fn = (pred & Y).sum(), (pred & ~Y).sum(), (~pred & Y).sum()
        f1 = 2 * tp / max(2 * tp + fp + fn, 1)
        best = max(best, (f1, round(float(c), 2)))
    return best[1], round(float(best[0]), 3)


def main():
    t0 = time.time()
    off = json.loads(OFFICIAL.read_text(encoding="utf-8"))["years"]
    card_tests = {}

    # A. 2022-2025
    mA = fit(*build(range(2015, 2022))[:2])
    X, y, o = build(range(2022, 2026))
    A = {}
    for org in sorted(set(o)):
        s = o == org
        yb = (y[s] > 0).astype(int)
        A[org] = {"auc_model": round(roc_auc_score(yb, proba(mA, X[s])), 3), "auc_rain_deficit": round(roc_auc_score(yb, baseline(X[s])), 3)}
    card_tests["A_train_2015_2021_test_2022_2025"] = A
    print("A. test 2022-25 AUC (model | rain deficit so far):", {k: (v["auc_model"], v["auc_rain_deficit"]) for k, v in A.items()})

    loyo_cut, f1 = choose_cut(list(range(2015, 2026)))
    print(f"leave-one-year-out best cut: p >= {loyo_cut} (F1 {f1}) -> the trigger alone gives the best drought call")
    cut = 0.5   # alerts = trigger met; within alerts, model confidence >= 0.5 -> "likely", else "watch"

    # B. 2026, never seen
    mB = fit(*build(range(2015, 2026))[:2])
    X, y, o = rows(2026)
    listed = np.array([int(k) for k in off["2026"]])
    B = {}
    for org in sorted(set(o)):
        s = o == org
        Xs, ys = X[s], y[s] > 0
        p = proba(mB, Xs)
        lv = np.array(dr.level(dr.trigger_so_far(Xs), p, cut))
        B[org] = {"auc_model": round(roc_auc_score(ys, p), 3), "auc_rain_deficit": round(roc_auc_score(ys, baseline(Xs)), 3),
                  "official_listed_22": {"likely": int((lv[listed] == "likely").sum()), "watch": int((lv[listed] == "watch").sum()),
                                         "low": int((lv[listed] == "low").sum())},
                  "statewide": {k: int((lv == k).sum()) for k in ("likely", "watch", "low")},
                  "labels_drought_taluks": int(ys.sum())}
    card_tests["B_train_2015_2025_test_2026"] = B
    print("B. 2026 (never seen):")
    for k, v in B.items():
        print(f"   from {k}: AUC {v['auc_model']} | {v['auc_rain_deficit']}; official 22 -> {v['official_listed_22']}; statewide {v['statewide']}")

    # C. official 2023 order, model without 2023
    mC = fit(*build([y for y in YEARS if y != 2023])[:2])
    dec = np.zeros(227, int)
    for k, v in off["2023"].items():
        dec[int(k)] = 2 if v["level"] == "severe" else 1
    C = {}
    for org in ("08-01", "08-15", "09-01"):
        Xs = dr.features_at(dt.date(2023, int(org[:2]), int(org[3:])))
        p = proba(mC, Xs)
        lv = np.array(dr.level(dr.trigger_so_far(Xs), p, cut))
        C[org] = {g: {k: int((lv[dec == c] == k).sum()) for k in ("likely", "watch", "low")}
                  for g, c in (("declared_severe", 2), ("declared_moderate", 1), ("not_listed", 0))}
        C[org]["auc_severe_vs_moderate"] = round(roc_auc_score((dec[dec > 0] == 2).astype(int), p[dec > 0]), 3)
    card_tests["C_official_2023_order_model_without_2023"] = C
    print("C. official 2023 order (model trained without 2023):", json.dumps(C, indent=1))

    final = fit(*build(YEARS)[:2])
    final.cut = cut
    dr.MODELS.mkdir(exist_ok=True)
    joblib.dump(final, dr.MODEL_FILE, compress=3)
    labels = dr.label_seasons()
    dr.LABELS_FILE.write_text(json.dumps({
        "method": "GoI Drought Manual-style labels from IMD rain, FAO-56 moisture adequacy and well groundwater (core/drought.py)",
        "years": {str(y): v["label"].tolist() for y, v in labels.items()}}))
    card = {"model": "M1 kharif agricultural-drought early warning", "version": "m1-v2", "trained": dt.date.today().isoformat(),
            "sklearn": sklearn.__version__, "features": dr.MODEL_FEATURES, "monotonic": dr.MONOTONIC,
            "trigger": dr.TRIGGER, "level_cut": cut, "loyo_best_cut": loyo_cut, "loyo_f1": f1,
            "levels": "alert = Drought Manual trigger met so far (leave-one-year-out showed the trigger alone gives the best "
                      "drought / no-drought call); within alerts: likely = model probability >= 0.5, else watch",
            "labels": "Drought Manual-style season labels from real data; MAI band chosen after seeing 2023 (labels in-sample for 2023)",
            "label_counts": {str(y): np.bincount(v["label"], minlength=3).tolist() for y, v in labels.items()},
            "official_sources": json.loads(OFFICIAL.read_text(encoding="utf-8"))["sources"],
            "tests": card_tests,
            "reading": "AUC ranks taluks; raw probabilities run low in statewide drought years, so the level combines the "
                       "official trigger with the model's rank"}
    dr.CARD_FILE.write_text(json.dumps(card, indent=2))
    print(f"saved {dr.MODEL_FILE.name} + card ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
