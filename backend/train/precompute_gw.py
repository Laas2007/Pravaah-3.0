"""Precompute M2 forecasts for every origin month so the API only looks them up (no live model runs).

    python train/precompute_gw.py          # ~15 min; re-run after train_gw.py or new well data

Writes models/gw_m2_forecasts.npz: per origin month the current taluk anomaly, the 10/50/90 % anomaly paths for the
next 6 months and the driver effects (m). core/gwmodel.predict() uses it automatically when present.
"""
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import gwmodel as gm  # noqa: E402

FIRST = "2015-01"


def main():
    t0 = time.time()
    models = gm.load()
    a = gm.arrays()
    months = [m for m in a["months"] if m >= FIRST and gm.month_end(m).isoformat() <= a["c"].dates[-1]]
    out = {k: [] for k in ("now", "p10", "p50", "p90", *[f"drv_{d}" for d in gm.DRIVER_KEYS])}
    for n, m in enumerate(months):
        o = gm.forecast_origin(models, a["months"].index(m))
        out["now"].append(o["now"])
        for p in (10, 50, 90):
            out[f"p{p}"].append(o["paths"][p])
        for d in gm.DRIVER_KEYS:
            out[f"drv_{d}"].append(o["drivers_m"][d])
        if n % 12 == 0:
            print(f"  {m} ({n + 1}/{len(months)}, {time.time() - t0:.0f}s)", flush=True)
    np.savez_compressed(gm.PRECOMPUTED, months=np.array(months),
                        **{k: np.array(v, dtype=np.float32) for k, v in out.items()})
    print(f"saved {gm.PRECOMPUTED.name} ({gm.PRECOMPUTED.stat().st_size / 1e6:.1f} MB), {len(months)} months, "
          f"{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
