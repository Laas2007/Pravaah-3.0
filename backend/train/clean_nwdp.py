"""Clean the NWDP downloads (train/fetch_nwdp.py) into compact files used by models and the API.

    python train/clean_nwdp.py              # groundwater + reservoirs + tanks
    python train/clean_nwdp.py groundwater

Outputs in data/karnataka/:
  gw_wells.json        every well: code, lat, lon, taluk idx, district, readings, median depth
  gw_taluk.npz         monthly per taluk (2005-01 .. latest): median depth to water (m below ground),
                       median anomaly vs each well's own 2014-2022 calendar-month normal (+ = deeper = worse),
                       number of wells
  reservoirs.json      metadata per reservoir + daily gross storage / inflow / outflow / canal withdrawal
  tanks_taluk.json     minor irrigation tanks aggregated per taluk (count, storage MCFT, command area ha)
"""
import difflib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from shapely import STRtree
from shapely.geometry import Point, shape

DATA = Path(__file__).resolve().parent.parent / "data"
DL = DATA / "_downloads" / "nwdp"
OUT = DATA / "karnataka"

NORMAL_YEARS = (2014, 2022)   # pre-2023-drought baseline, same idea as the Bengaluru model's rain normal
START_MONTH = "2005-01"
TAMIL_NADU = {"Mettur", "Bhavani", "Amaravathy"}   # Cauvery-basin context only, not Karnataka storage
# Abbreviations fuzzy matching gets wrong, and taluks created after the 2018 boundaries (-> parent taluk).
TALUK_ALIAS = {
    "H D Kote": "Heggadadevankote", "H B Halli": "Hagaribommanahalli", "Hulsur": "Hulsoor",
    "T Narsipur": "Tirumakudal - Narsipur", "K.G.F": "Kolar Gold Field", "N R Pura": "Narasimharajapura",
    "Virarajendrapet": "Virajpet", "Kuknur": "Kukunoor", "Joida": "Supa",
    "Ponnampete": "Virajpet", "Harohalli": "Kanakapura", "Yaragatti": "Savadatti",
}


def read(name):
    d = pd.read_csv(DL / f"{name}.csv", dtype=str)
    d.columns = [" ".join(c.split()) for c in d.columns]   # headers contain stray newlines
    return d


def load_taluks():
    regions = json.loads((OUT / "regions.json").read_text(encoding="utf-8"))["taluks"]
    geoms = {f["properties"]["id"]: shape(f["geometry"])
             for f in json.loads((OUT / "taluks.geojson").read_text(encoding="utf-8"))["features"]}
    return regions, [geoms[r["id"]] for r in regions]


def assign_taluk(lat, lon, geoms, max_km=8):
    """Index of the taluk containing each point; nearest taluk within max_km for points just outside
    (simplified boundaries, coastal wells); -1 otherwise."""
    tree = STRtree(geoms)
    out = np.full(len(lat), -1)
    for k, (la, lo) in enumerate(zip(lat, lon)):
        p = Point(lo, la)
        hit = [i for i in tree.query(p) if geoms[i].contains(p)]
        if hit:
            out[k] = hit[0]
        else:
            i = tree.nearest(p)
            if geoms[i].distance(p) * 111 < max_km:
                out[k] = i
    return out


def dump(path, obj):
    path.write_text(json.dumps(obj, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    print(f"  wrote {path.relative_to(DATA.parent)} ({path.stat().st_size / 1e6:.2f} MB)")


# ---------------------------------------------------------------- groundwater

def groundwater():
    print("groundwater")
    d = pd.concat([read(n) for n in ("gwl_monthly_1971-2020", "gwl_monthly_2021-2025", "gwl_monthly_2026-2030")])
    d = pd.DataFrame({
        "well": d["Station Code"].str.lstrip("0"),
        "district": d["District"],
        "lat": pd.to_numeric(d["Latitude"], errors="coerce"),
        "lon": pd.to_numeric(d["Longitude"], errors="coerce"),
        "month": pd.to_datetime(d["Monitoring Date"], format="%d-%m-%Y", errors="coerce").dt.to_period("M"),
        "depth": pd.to_numeric(d["Ground Water Level"], errors="coerce"),
    }).dropna()
    n0 = len(d)
    # NWDP stores "not measured yet" as -0.05 (about 150-290 wells a month since 2024, nearly every well from Jul 2026)
    # and a few rows as exactly 0. Neither is a reading: a depth <= 0 would mean water at or above ground level.
    placeholder = d.depth <= 0
    d = d[~placeholder]
    print(f"  {int(placeholder.sum())} placeholder readings (<= 0 m) dropped")
    d = d[d.month >= pd.Period(START_MONTH, "M")]
    d = d.groupby(["well", "month"], as_index=False).agg(
        depth=("depth", "median"), lat=("lat", "first"), lon=("lon", "first"), district=("district", "first"))
    # Per-well outliers (typos like 597 m): drop readings far outside the well's own range.
    med = d.groupby("well").depth.transform("median")
    mad = d.groupby("well").depth.transform(lambda s: (s - s.median()).abs().median()).clip(lower=0.5)
    bad = (d.depth - med).abs() > 8 * mad
    d = d[~bad]
    print(f"  {n0} raw readings -> {len(d)} well-months since {START_MONTH} ({int(bad.sum())} outliers dropped)")

    # Anomaly vs the well's own calendar-month normal (needs >= 4 normal-period years for that month).
    d["cal"] = d.month.dt.month
    yr = d.month.dt.year
    norm = (d[(yr >= NORMAL_YEARS[0]) & (yr <= NORMAL_YEARS[1])]
            .groupby(["well", "cal"]).depth.agg(["median", "size"]).reset_index())
    norm = norm[norm["size"] >= 4].rename(columns={"median": "normal"})[["well", "cal", "normal"]]
    d = d.merge(norm, on=["well", "cal"], how="left")
    d["anom"] = d.depth - d.normal

    regions, geoms = load_taluks()
    wells = d.groupby("well").agg(lat=("lat", "first"), lon=("lon", "first"), district=("district", "first"),
                                  n=("depth", "size"), depth=("depth", "median")).reset_index()
    wells["taluk"] = assign_taluk(wells.lat.values, wells.lon.values, geoms)
    print(f"  {len(wells)} wells, {int((wells.taluk < 0).sum())} outside Karnataka taluks (dropped)")
    wells = wells[wells.taluk >= 0]
    d = d.merge(wells[["well", "taluk"]], on="well")

    months = pd.period_range(START_MONTH, d.month.max(), freq="M")
    T = len(regions)
    depth = np.full((len(months), T), np.nan, dtype=np.float32)
    anom = np.full((len(months), T), np.nan, dtype=np.float32)
    nwell = np.zeros((len(months), T), dtype=np.int16)
    mi = {m: k for k, m in enumerate(months)}
    g = d.groupby(["month", "taluk"]).agg(depth=("depth", "median"), anom=("anom", "median"), n=("depth", "size"))
    for (m, t), row in g.iterrows():
        depth[mi[m], t], anom[mi[m], t], nwell[mi[m], t] = row.depth, row.anom, row.n
    np.savez_compressed(OUT / "gw_taluk.npz", months=np.array([str(m) for m in months]),
                        ids=np.array([r["id"] for r in regions]), depth=depth, anom=anom, wells=nwell)
    covered = (nwell[-24:] > 0).any(axis=0).sum()
    print(f"  wrote gw_taluk.npz ({len(months)} months x {T} taluks); {covered}/{T} taluks have wells in the last 2 years")

    # well x month depth matrix (cleaned readings) for the well-level M2 model
    wcode = list(wells.well)
    wi = {c: j for j, c in enumerate(wcode)}
    W = np.full((len(wcode), len(months)), np.nan, dtype=np.float32)
    W[d.well.map(wi).values, d.month.map(mi).values] = d.depth.values
    np.savez_compressed(OUT / "gw_well_monthly.npz", months=np.array([str(m) for m in months]),
                        wells=np.array(wcode), taluk=wells.taluk.values.astype(np.int16), depth=W)
    print(f"  wrote gw_well_monthly.npz ({W.shape[0]} wells x {W.shape[1]} months, {np.isfinite(W).mean():.0%} filled)")

    dump(OUT / "gw_wells.json", {
        "source": "NWDP Ground Water Level Manual Monthly Karnataka (Karnataka Ground Water Directorate)",
        "units": "depth to water, m below ground level",
        "wells": [{"code": r.well, "lat": round(r.lat, 5), "lon": round(r.lon, 5), "taluk": int(r.taluk),
                   "district": r.district, "readings": int(r.n), "median_depth_m": round(float(r.depth), 2)}
                  for r in wells.itertuples()]})

    # quick plausibility print: state-wide median anomaly in May (pre-monsoon) by year
    may = [k for k, m in enumerate(months) if m.month == 5]
    print("  pre-monsoon (May) median anomaly across taluks, m (+ = deeper than normal):")
    print("   " + "  ".join(f"{months[k].year}:{np.nanmedian(anom[k]):+.1f}" for k in may if months[k].year >= 2014))


# ---------------------------------------------------------------- reservoirs

def reservoirs():
    print("reservoirs")
    d = read("reservoirs_daily_1990-2026")
    num = lambda c: pd.to_numeric(d[c], errors="coerce")
    r = pd.DataFrame({
        "name": d["Reservoir Name"].str.strip(), "basin": d["Basin"], "river": d["River"],
        "date": pd.to_datetime(d["Monitoring Date"].str[:10], format="%d-%m-%Y", errors="coerce"),
        "design": num("Design Gross Capacity (TMC)"), "gross": num("Gross Capacity (TMC)"),
        "live": num("Live Capacity (TMC)"), "level_ft": num("Reservoir Level (ft)"),
        "inflow": num("Inflow (Cusecs)"), "outflow": num("Outflow to River (Cusecs)"),
        "canal": num("Canal Withdrawal (Cusecs)"),
    }).dropna(subset=["date"])
    r = r.sort_values("date").groupby(["name", "date"], as_index=False).last()

    out = []
    for name, g in r.groupby("name"):
        design = float(g.design.max())
        g = g.set_index("date")
        gross = g.gross.where((g.gross >= 0) & (g.gross <= design * 1.05))  # unit/typo errors -> NaN
        # Drop isolated jumps: > 25 % of capacity away from the 7-day rolling median.
        roll = gross.rolling(7, center=True, min_periods=3).median()
        gross = gross.where((gross - roll).abs() <= 0.25 * design)
        dropped = int(g.gross.notna().sum() - gross.notna().sum())
        days = pd.date_range(g.index.min(), g.index.max(), freq="D")
        gross = gross.reindex(days).interpolate(limit=7)   # fill gaps up to a week
        clean = lambda s: [None if pd.isna(x) else round(float(x), 3) for x in s.reindex(days)]
        out.append({
            "name": name, "basin": g.basin.iloc[0], "river": g.river.iloc[0],
            "state": "Tamil Nadu" if name in TAMIL_NADU else "Karnataka",
            "design_gross_tmc": design, "start": str(days[0].date()), "end": str(days[-1].date()),
            "days": len(days), "valid_days": int(gross.notna().sum()), "dropped_bad_readings": dropped,
            "gross_tmc": clean(gross),
            "inflow_cusecs": [None if pd.isna(x) else int(x) for x in g.inflow.reindex(days)],
            "outflow_cusecs": [None if pd.isna(x) else int(x) for x in g.outflow.reindex(days)],
            "canal_cusecs": [None if pd.isna(x) else int(x) for x in g.canal.reindex(days)],
        })
        print(f"  {name:32s} {out[-1]['start']}..{out[-1]['end']}  design {design:7.2f} TMC  "
              f"valid {out[-1]['valid_days']}/{len(days)}  dropped {dropped}")
    dump(OUT / "reservoirs.json", {
        "source": "NWDP Reservoir Data (Manual Daily) Karnataka (Karnataka Water Resources Dept)",
        "units": {"storage": "TMC (1 TMC = 28.317 million m3)", "flows": "cusecs"},
        "reservoirs": sorted(out, key=lambda x: -x["design_gross_tmc"])})


# ---------------------------------------------------------------- tanks

def tanks():
    print("tanks")
    d = read("minor_irrigation_tanks")
    regions, _ = load_taluks()
    norm = lambda s: "".join(ch for ch in str(s).lower() if ch.isalnum())
    by_name = {}
    for r in regions:
        by_name.setdefault(norm(r["name"]), r["idx"])

    def match(s):
        # alias, then exact after normalising, else closest spelling ("Chik Ballapur" -> "Chikkaballapura")
        n = norm(TALUK_ALIAS.get(str(s).strip(), s))
        if n in by_name:
            return by_name[n]
        close = difflib.get_close_matches(n, by_name, n=1, cutoff=0.75)
        return by_name[close[0]] if close else -1
    d["taluk"] = d["Taluk"].map(match)
    for c in ("Storage Capacity (MCFT)", "Command Area (Ha)", "Tank Spread Area (Ha)"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    miss = sorted(d.loc[d.taluk < 0, "Taluk"].dropna().unique())
    print(f"  {len(d)} tanks, {int((d.taluk >= 0).sum())} matched to a taluk; unmatched names: {miss[:15]}")
    g = d[d.taluk >= 0].groupby("taluk").agg(tanks=("Tank ID", "size"), storage_mcft=("Storage Capacity (MCFT)", "sum"),
                                             command_ha=("Command Area (Ha)", "sum"), spread_ha=("Tank Spread Area (Ha)", "sum"))
    dump(OUT / "tanks_taluk.json", {
        "source": "NWDP Minor Irrigation Tank Karnataka", "unmatched_taluk_names": miss,
        "taluks": {int(t): {k: round(float(v), 1) for k, v in row.items()} for t, row in g.iterrows()}})


if __name__ == "__main__":
    steps = {"groundwater": groundwater, "reservoirs": reservoirs, "tanks": tanks}
    for s in sys.argv[1:] or list(steps):
        steps[s]()
