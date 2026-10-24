"""Check the Bengaluru ward model's simulated groundwater against real NWDP monitoring wells in/around the city.

    python train/validate_bengaluru.py            # report for the current model.Params
    python train/validate_bengaluru.py --search   # also grid-search Params on 2015-2021 and report 2022+ (held out)

The ward model (backend/model.py) simulates a groundwater store per ward per day. Wells measure depth to water.
Both are turned into monthly anomalies vs their own 2014-2021 calendar-month normal; the simulated store is compared
with the (sign-flipped) depth anomaly of each well inside a ward or within 3 km of the city (nearest ward).
"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np
from shapely import STRtree
from shapely.geometry import Point, shape
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import model  # noqa: E402
from core import gwmodel as gm  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data"
CARD = Path(__file__).resolve().parent.parent / "models" / "bengaluru_validation.json"


def wells_near_city():
    gj = json.loads((DATA / "bbmp_wards.geojson").read_text(encoding="utf-8"))
    polys = [shape(f["geometry"]).buffer(0) for f in gj["features"]]
    city = unary_union(polys).buffer(0.027)          # ~3 km
    tree = STRtree(polys)
    w = model.load_world()
    meta = json.loads((DATA / "karnataka" / "gw_wells.json").read_text(encoding="utf-8"))["wells"]
    a = gm.arrays()
    code_idx = {c: k for k, c in enumerate(np.load(DATA / "karnataka" / "gw_well_monthly.npz")["wells"])}
    out = []
    for m in meta:
        p = Point(m["lon"], m["lat"])
        if not city.contains(p) or m["code"] not in code_idx:
            continue
        hit = [i for i in tree.query(p) if polys[i].contains(p)]
        ward = hit[0] if hit else int(np.argmin((w.lat - m["lat"]) ** 2 + (w.lon - m["lon"]) ** 2))
        out.append({"code": m["code"], "row": code_idx[m["code"]], "ward": int(ward), "inside": bool(hit)})
    return out, a


def monthly_store(p):
    """Simulated store per ward, monthly mean, aligned to the well months (YYYY-MM)."""
    w = model.load_world()
    hist = model.simulate_history(p)
    months = np.array([d[:7] for d in w.dates])
    keys = sorted(set(months))
    return keys, np.stack([hist[months == k].mean(axis=0) for k in keys])


def evaluate(p, wells, a):
    keys, S = monthly_store(p)
    wm = a["months"]
    common = [m for m in keys if m in wm]
    ks = [keys.index(m) for m in common]
    kw = [wm.index(m) for m in common]
    cal = np.array([int(m[5:7]) for m in common])
    yr = np.array([int(m[:4]) for m in common])
    norm = (yr >= 2014) & (yr <= 2021)
    Ssub = S[ks]
    S_anom = Ssub - np.stack([np.nanmean(Ssub[norm & (cal == c)], axis=0) for c in range(1, 13)])[cal - 1]
    res = []
    for wl in wells:
        dep = a["W"][wl["row"], kw]
        dn = np.array([np.nanmedian(dep[norm & (cal == c)]) if np.isfinite(dep[norm & (cal == c)]).sum() >= 3 else np.nan
                       for c in range(1, 13)])
        A = dep - dn[cal - 1]                                   # + = deeper than normal
        s = S_anom[:, wl["ward"]]
        r = {}
        for name, sel in (("train", yr <= 2021), ("test", yr >= 2022), ("all", yr > 0)):
            ok = sel & np.isfinite(A) & np.isfinite(s)
            r[name] = float(np.corrcoef(s[ok], -A[ok])[0, 1]) if ok.sum() >= 12 and np.std(A[ok]) > 0 else np.nan
        res.append({**wl, **{f"r_{k}": v for k, v in r.items()}})
    return res


def summary(res):
    out = {}
    for k in ("train", "test", "all"):
        v = np.array([r[f"r_{k}"] for r in res])
        v = v[np.isfinite(v)]
        out[k] = {"wells": int(len(v)), "median_r": round(float(np.median(v)), 2) if len(v) else None,
                  "share_positive": round(float(np.mean(v > 0)), 2) if len(v) else None}
    return out


def main():
    wells, a = wells_near_city()
    print(f"{len(wells)} wells within ~3 km of BBMP ({sum(w['inside'] for w in wells)} inside a ward)")
    base = model.Params()
    res = evaluate(base, wells, a)
    s0 = summary(res)
    print("current Params:", s0)
    report = {"wells": len(wells), "current_params": s0, "per_well": res}

    if "--search" in sys.argv:
        grid = {"capacity_mm": [200.0, 300.0, 450.0], "lam": [1 / 90, 1 / 150, 1 / 300], "reg_k": [0.5, 1.0, 1.5]}
        best = None
        for vals in itertools.product(*grid.values()):
            p = model.Params(**dict(zip(grid, vals)))
            sm = summary(evaluate(p, wells, a))
            score = sm["train"]["median_r"] or -1
            print(f"  {dict(zip(grid, [round(v, 4) for v in vals]))} train r={sm['train']['median_r']} test r={sm['test']['median_r']}")
            if best is None or score > best[0]:
                best = (score, vals, sm)
        print("best on 2015-2021:", dict(zip(grid, best[1])), "-> held-out 2022+:", best[2]["test"])
        report["search"] = {"grid": {k: [float(x) for x in v] for k, v in grid.items()},
                            "best_params": dict(zip(grid, [float(x) for x in best[1]])), "best_summary": best[2]}
    CARD.write_text(json.dumps(report, indent=2))
    print(f"wrote {CARD.name}")


if __name__ == "__main__":
    main()
