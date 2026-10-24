"""Time Machine data: M2 forecasts made by a model that never saw the years it is replayed on.

    python train/precompute_backtest.py        # ~10 min

Fits the validation models exactly as train_gw.py does (targets <= 2021-12, same subsample) and precomputes their
forecasts for every origin month from 2022-01, so replaying any date from 2022 on is a genuine out-of-sample test.
Writes models/gw_m2_backtest.npz (same layout as gw_m2_forecasts.npz). Earlier dates use the production forecasts
and are labelled "in-sample" in the API.
"""
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import train_gw as T  # noqa: E402
from core import gwmodel as gm  # noqa: E402

OUT = gm.MODELS / "gw_m2_backtest.npz"


def main():
    t0 = time.time()
    a = gm.arrays()
    months = a["months"]
    X, y, meta = T.build_panel()
    K, J, H = meta.T
    targ = np.array(months)[np.minimum(K + H, len(months) - 1)]
    tri = T.subsample(np.where(targ <= T.TRAIN_TARGET_UNTIL)[0], T.MAX_TRAIN_ROWS)
    vm = {q: T.fit(X[tri], y[tri], q) for q in gm.QUANTILES}
    print(f"validation models fitted ({time.time() - t0:.0f}s)", flush=True)
    origins = [m for m in months if m >= T.TEST_ORIGIN_FROM and gm.month_end(m).isoformat() <= a["c"].dates[-1]]
    out = {k: [] for k in ("now", "p10", "p50", "p90", *[f"drv_{d}" for d in gm.DRIVER_KEYS])}
    for n, m in enumerate(origins):
        o = gm.forecast_origin(vm, months.index(m))
        out["now"].append(o["now"])
        for p in (10, 50, 90):
            out[f"p{p}"].append(o["paths"][p])
        for d in gm.DRIVER_KEYS:
            out[f"drv_{d}"].append(o["drivers_m"][d])
        if n % 12 == 0:
            print(f"  {m} ({n + 1}/{len(origins)}, {time.time() - t0:.0f}s)", flush=True)
    np.savez_compressed(OUT, months=np.array(origins), trained_until=np.array(T.TRAIN_TARGET_UNTIL),
                        **{k: np.array(v, dtype=np.float32) for k, v in out.items()})
    print(f"saved {OUT.name}, {len(origins)} months, {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
