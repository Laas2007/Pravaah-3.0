"""Build the Karnataka base data used by every platform.

    python train/fetch_karnataka.py boundaries   # taluk + district geojson, regions.json
    python train/fetch_karnataka.py imd          # IMD gauge-based gridded rain -> per-taluk daily rain
    python train/fetch_karnataka.py era5         # ERA5 (Open-Meteo) ET0, Tmax, Tmin, rain on a 0.5 deg grid
    python train/fetch_karnataka.py climate      # merge: IMD rain + bias-corrected ERA5 rain for the
                                                 # months IMD hasn't published yet; ERA5-vs-IMD bias table
    python train/fetch_karnataka.py all

Sources (all free, no key):
  Taluks     geoBoundaries IND ADM3 (2018, from the government's LGD directory)
  Districts  datta07/INDIAN-SHAPEFILES Karnataka districts (Census 2011 + LGD codes), plus Vijayanagara (2021)
  Rain       IMD Pune 0.25 deg gridded daily rainfall (interpolated rain-gauge data), yearly binary files
  ET0, temp  Open-Meteo historical archive (ERA5 reanalysis)

Big source files go to data/_downloads/ (git-ignored); outputs go to data/karnataka/.
"""
import datetime as dt
import json
import re
import sys
import time
from pathlib import Path

import httpx
import numpy as np
from shapely.geometry import box, mapping, shape
from shapely.ops import unary_union

DATA = Path(__file__).resolve().parent.parent / "data"
DL = DATA / "_downloads"
OUT = DATA / "karnataka"

GB_ADM3 = "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/IND/ADM3/geoBoundaries-IND-ADM3.geojson"
DATTA = "https://raw.githubusercontent.com/datta07/INDIAN-SHAPEFILES/master/STATES/KARNATAKA/"
IMD_URL = "https://www.imdpune.gov.in/cmpg/Griddata/rainfall.php"
ERA5_URL = "https://archive-api.open-meteo.com/v1/archive"

START = "2014-01-01"
IMD_YEARS = range(2014, 2026)
# Vijayanagara district was carved out of Ballari in 2021 (the boundary files predate it).
VIJAYANAGARA = {"Hosapete", "Kudligi", "Hagaribommanahalli", "Hadagalli", "Harapanahalli", "Kotturu"}
DISTRICT_RENAME = {"Bangalore": "Bengaluru Urban"}
ERA5_STEP = 0.5          # deg; ET0/temperature are smooth fields, so a coarse grid is enough
ERA5_VARS = ["precipitation_sum", "et0_fao_evapotranspiration", "temperature_2m_max", "temperature_2m_min"]


def download(url, path, data=None):
    if path.exists() and path.stat().st_size > 0:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    print(f"  downloading {path.name} ...")
    with httpx.stream("POST" if data else "GET", url, data=data, timeout=600, follow_redirects=True) as r:
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_bytes():
                f.write(chunk)
    return path


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def tidy(name):
    """'HUBBALLI URBAN' -> 'Hubballi Urban'; leave mixed-case names alone."""
    return name.title() if name.isupper() else name


def round_coords(geom, nd=4):
    def r(c):
        return [r(x) for x in c] if isinstance(c[0], (list, tuple)) else [round(c[0], nd), round(c[1], nd)]
    g = mapping(geom)
    return {"type": g["type"], "coordinates": r(g["coordinates"])}


# ---------------------------------------------------------------- boundaries

def boundaries():
    print("boundaries")
    state = shape(json.loads(download(DATTA + "KARNATAKA_STATE.geojson", DL / "ka_state_datta.geojson").read_text())
                  ["features"][0]["geometry"]).buffer(0)
    dists = [(f["properties"]["dtname"], f["properties"].get("Dist_LGD"), shape(f["geometry"]).buffer(0))
             for f in json.loads(download(DATTA + "KARNATAKA_DISTRICTS.geojson", DL / "ka_districts_datta.geojson")
                                 .read_text(encoding="utf-8"))["features"]]
    adm3 = json.loads(download(GB_ADM3, DL / "ind_adm3.geojson").read_text(encoding="utf-8"))

    taluks = []
    for f in adm3["features"]:
        g = shape(f["geometry"])
        if not g.intersects(state.envelope):
            continue
        g = g.buffer(0)
        if g.intersection(state).area / g.area <= 0.5:
            continue
        name = tidy(f["properties"]["shapeName"].strip())
        dname, dcode, _ = max(dists, key=lambda d: d[2].intersection(g).area)
        dname = DISTRICT_RENAME.get(dname, dname)
        if name in VIJAYANAGARA:
            dname, dcode = "Vijayanagara", None
        taluks.append({"name": name, "district": dname, "district_lgd": dcode, "geom": g})

    taluks.sort(key=lambda t: (t["district"], t["name"]))
    ids = [f"KA-{slug(t['district'])}-{slug(t['name'])}" for t in taluks]
    assert len(set(ids)) == len(ids), "duplicate taluk ids"

    regions, feats = [], []
    for i, (tid, t) in enumerate(zip(ids, taluks)):
        g = t["geom"]
        c = g.representative_point()
        lat0 = c.y
        area = g.area * 111.32 * np.cos(np.radians(lat0)) * 110.57
        meta = {"idx": i, "id": tid, "name": t["name"], "district": t["district"],
                "lat": round(c.y, 4), "lon": round(c.x, 4), "area_km2": round(float(area), 1)}
        regions.append(meta)
        feats.append({"type": "Feature", "properties": {k: meta[k] for k in ("idx", "id", "name", "district")},
                      "geometry": round_coords(g.simplify(0.003, preserve_topology=True))})

    dfeats = []
    for d in sorted({t["district"] for t in taluks}):
        g = unary_union([t["geom"] for t in taluks if t["district"] == d]).buffer(0)
        dfeats.append({"type": "Feature", "properties": {"id": f"KA-{slug(d)}", "name": d,
                                                          "taluks": sum(t["district"] == d for t in taluks)},
                       "geometry": round_coords(g.simplify(0.004, preserve_topology=True))})

    OUT.mkdir(parents=True, exist_ok=True)
    dump(OUT / "taluks.geojson", {"type": "FeatureCollection", "features": feats})
    dump(OUT / "districts.geojson", {"type": "FeatureCollection", "features": dfeats})
    dump(OUT / "regions.json", {"source": "geoBoundaries IND ADM3 2018 (LGD); districts datta07 + Vijayanagara 2021",
                                "taluks": regions})
    print(f"  {len(regions)} taluks in {len(dfeats)} districts")


def dump(path, obj):
    path.write_text(json.dumps(obj, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    print(f"  wrote {path.relative_to(DATA.parent)} ({path.stat().st_size / 1e6:.2f} MB)")


def load_regions():
    regions = json.loads((OUT / "regions.json").read_text(encoding="utf-8"))["taluks"]
    geoms = {f["properties"]["id"]: shape(f["geometry"])
             for f in json.loads((OUT / "taluks.geojson").read_text(encoding="utf-8"))["features"]}
    return regions, [geoms[r["id"]] for r in regions]


# ---------------------------------------------------------------- IMD rain

IMD_LAT = 6.5 + 0.25 * np.arange(129)
IMD_LON = 66.5 + 0.25 * np.arange(135)


def imd_year(y):
    a = np.fromfile(download(IMD_URL, DL / "imd" / f"{y}.grd", data={"rain": str(y)}), "<f4")
    return a.reshape(-1, 129, 135)  # (day, lat, lon); -999 = no data (sea / outside India)


def imd():
    """Daily rain per taluk = area-weighted mean of the 0.25 deg IMD cells it overlaps."""
    print("imd")
    regions, geoms = load_regions()
    first = imd_year(IMD_YEARS[0])
    land = first[0] > -900
    weights = []  # per taluk: (lat_idx, lon_idx, weight)
    for g in geoms:
        x0, y0, x1, y1 = g.bounds
        cells = []
        for i in np.where((IMD_LAT >= y0 - 0.25) & (IMD_LAT <= y1 + 0.25))[0]:
            for j in np.where((IMD_LON >= x0 - 0.25) & (IMD_LON <= x1 + 0.25))[0]:
                if not land[i, j]:
                    continue
                a = g.intersection(box(IMD_LON[j] - .125, IMD_LAT[i] - .125, IMD_LON[j] + .125, IMD_LAT[i] + .125)).area
                if a > 0:
                    cells.append((i, j, a))
        w = np.array([c[2] for c in cells])
        weights.append((np.array([c[0] for c in cells]), np.array([c[1] for c in cells]), w / w.sum()))

    dates, rows = [], []
    for y in IMD_YEARS:
        a = first if y == IMD_YEARS[0] else imd_year(y)
        a = np.where(a < -900, np.nan, a)
        d0 = dt.date(y, 1, 1)
        dates += [(d0 + dt.timedelta(days=k)).isoformat() for k in range(a.shape[0])]
        rows.append(np.stack([np.nansum(a[:, ii, jj] * w, axis=1) for ii, jj, w in weights], axis=1))
        print(f"  {y}: {a.shape[0]} days")
    rain = np.vstack(rows).astype(np.float32)
    np.savez_compressed(OUT / "rain_imd.npz", dates=np.array(dates), rain=rain,
                        ids=np.array([r["id"] for r in regions]))
    print(f"  wrote rain_imd.npz {rain.shape}, {dates[0]} .. {dates[-1]}")


# ---------------------------------------------------------------- ERA5

def era5_grid(state):
    pts = []
    area = state.simplify(0.01).buffer(0.3)
    for la in np.arange(11.5, 18.75, ERA5_STEP):
        for lo in np.arange(74.0, 78.75, ERA5_STEP):
            if area.contains(shape({"type": "Point", "coordinates": [lo, la]})):
                pts.append((round(float(la), 2), round(float(lo), 2)))
    return pts


def era5():
    print("era5")
    state = shape(json.loads((DL / "ka_state_datta.geojson").read_text())["features"][0]["geometry"]).buffer(0)
    pts = era5_grid(state)
    end = (dt.date.today() - dt.timedelta(days=6)).isoformat()
    print(f"  {len(pts)} grid points, {START} .. {end}")
    cache = DL / "era5"
    cache.mkdir(parents=True, exist_ok=True)
    chunks = [pts[k:k + 5] for k in range(0, len(pts), 5)]
    bodies, got, daily_limit = [], [], False
    for n, chunk in enumerate(chunks):
        f = cache / f"chunk_{n:03d}_{end}.json"
        if not f.exists() and not daily_limit:
            for attempt in range(6):
                try:
                    r = httpx.get(ERA5_URL, timeout=300, params={
                        "latitude": ",".join(str(p[0]) for p in chunk), "longitude": ",".join(str(p[1]) for p in chunk),
                        "start_date": START, "end_date": end, "daily": ",".join(ERA5_VARS), "timezone": "Asia/Kolkata"})
                except httpx.TransportError as e:  # flaky DNS / connection drops
                    print(f"  network error ({e}), retrying in 20s")
                    time.sleep(20)
                    continue
                if "daily api request limit" in r.text.lower():
                    daily_limit = True
                    break
                if r.status_code == 429 or (r.status_code == 400 and "limit" in r.text.lower()):
                    wait = 65 * (attempt + 1)
                    print(f"  rate limited ({r.text[:80]}), waiting {wait}s")
                    time.sleep(wait)
                    continue
                r.raise_for_status()
                f.write_text(r.text)
                break
            else:
                raise RuntimeError("Open-Meteo kept rate-limiting; re-run later (finished chunks are cached)")
            if not daily_limit:
                print(f"  chunk {n + 1}/{len(chunks)}")
                time.sleep(3)
        if not f.exists():
            continue
        b = json.loads(f.read_text())
        bodies += b if isinstance(b, list) else [b]
        got += chunk

    if len(got) < len(pts):
        # Taluks map to the nearest point we have, so a partial grid still works; re-run to complete it.
        print(f"  WARNING: Open-Meteo daily limit hit; using {len(got)}/{len(pts)} points. Re-run tomorrow to fill the rest.")
    complete = len(got) == len(pts)
    pts = got
    dates = bodies[0]["daily"]["time"]
    out = {"dates": np.array(dates), "lat": np.array([p[0] for p in pts]), "lon": np.array([p[1] for p in pts]),
           "complete": np.array(complete)}
    for v in ERA5_VARS:
        out[v] = np.array([[np.nan if x is None else x for x in b["daily"][v]] for b in bodies], dtype=np.float32).T
    np.savez_compressed(OUT / "era5_grid.npz", **out)
    print(f"  wrote era5_grid.npz ({len(dates)} days x {len(pts)} points)")


# ---------------------------------------------------------------- merge + bias check

def climate():
    """climate.npz: daily rain, et0, tmax, tmin per taluk on one date axis.

    Rain: IMD (gauge based) wherever IMD has published; after that, ERA5 rain scaled by the per-taluk,
    per-calendar-month IMD/ERA5 ratio over the overlap period. ET0/temperature: ERA5 at the nearest grid
    point. Also writes rain_bias.json (ERA5 vs IMD annual totals per district) for the model card.
    """
    print("climate")
    regions, _ = load_regions()
    imd_ = np.load(OUT / "rain_imd.npz")
    e = np.load(OUT / "era5_grid.npz")
    lat = np.array([r["lat"] for r in regions])
    lon = np.array([r["lon"] for r in regions])
    near = np.argmin((lat[:, None] - e["lat"][None]) ** 2 + (lon[:, None] - e["lon"][None]) ** 2, axis=1)

    edates = list(e["dates"])
    idates = list(imd_["dates"])
    assert edates[0] == idates[0], "IMD and ERA5 must start on the same day"
    n_imd = len(idates)
    era = {v: e[v][:, near] for v in ERA5_VARS}          # (days, taluks)
    era_rain = era["precipitation_sum"]
    imd_rain = imd_["rain"]

    months = np.array([int(d[5:7]) for d in edates])
    ratio = np.ones((12, len(regions)), dtype=np.float32)
    for m in range(1, 13):
        sel = months[:n_imd] == m
        ratio[m - 1] = np.clip(imd_rain[sel].sum(0) / np.maximum(era_rain[:n_imd][sel].sum(0), 1), 0.3, 3.0)
    era_corr = era_rain * ratio[months - 1]

    # IMD gaps: some cells report ~0 for whole months while every neighbour got rain (missing gauge reports
    # stored as zero, e.g. Bengaluru East in 2024). Replace those taluk-months with bias-corrected ERA5.
    nb = np.argsort(np.hypot(lat[:, None] - lat[None], lon[:, None] - lon[None]), axis=1)[:, 1:7]
    ym = np.array([d[:7] for d in idates])
    imd_rain = imd_rain.copy()
    patched = []
    for k in sorted(set(ym)):
        sel = ym == k
        tot = imd_rain[sel].sum(0)
        nbm = np.median(tot[nb], axis=1)
        for j in np.where((nbm > 40) & (tot < 0.25 * nbm))[0]:
            imd_rain[sel, j] = era_corr[:n_imd][sel, j]
            patched.append({"month": k, "taluk": regions[j]["name"], "imd_mm": round(float(tot[j])),
                            "neighbours_mm": round(float(nbm[j])), "era5_corr_mm": round(float(imd_rain[sel, j].sum()))})
    print(f"  patched {len(patched)} taluk-months where IMD reported ~0 but neighbours had rain")

    rain = np.vstack([imd_rain, era_corr[n_imd:]]).astype(np.float32)

    np.savez_compressed(
        OUT / "climate.npz", dates=np.array(edates), ids=np.array([r["id"] for r in regions]),
        rain=rain, et0=era["et0_fao_evapotranspiration"], tmax=era["temperature_2m_max"],
        tmin=era["temperature_2m_min"], rain_source_imd_until=np.array(idates[-1]))
    print(f"  wrote climate.npz ({len(edates)} days x {len(regions)} taluks); rain = IMD until {idates[-1]}, "
          f"bias-corrected ERA5 after")

    # bias table: annual totals, district means
    districts = sorted({r["district"] for r in regions})
    didx = {d: [i for i, r in enumerate(regions) if r["district"] == d] for d in districts}
    table = {"note": "Annual rainfall (mm), mean over each district's taluks. IMD = gauge-based grid; "
                     "ERA5 = reanalysis via Open-Meteo.", "years": [], "districts": {}}
    yrs = sorted({d[:4] for d in idates})
    for y in yrs:
        sel = np.array([d[:4] == y for d in idates])
        if sel.sum() < 365:
            continue
        table["years"].append(y)
        for d, ii in didx.items():
            row = table["districts"].setdefault(d, {"imd": [], "era5": []})
            row["imd"].append(round(float(imd_rain[sel][:, ii].sum(0).mean())))
            row["era5"].append(round(float(era_rain[:n_imd][sel][:, ii].sum(0).mean())))
    state_imd = np.array([np.mean([table["districts"][d]["imd"][k] for d in districts]) for k in range(len(table["years"]))])
    state_era = np.array([np.mean([table["districts"][d]["era5"][k] for d in districts]) for k in range(len(table["years"]))])
    table["state"] = {"imd": state_imd.round().tolist(), "era5": state_era.round().tolist()}
    table["imd_patched_months"] = patched
    dump(OUT / "rain_bias.json", table)
    print("\n  year   IMD   ERA5  ERA5 vs IMD")
    for y, a, b in zip(table["years"], state_imd, state_era):
        print(f"  {y}  {a:5.0f}  {b:5.0f}  {100 * (b / a - 1):+5.0f}%")


if __name__ == "__main__":
    steps = {"boundaries": boundaries, "imd": imd, "era5": era5, "climate": climate}
    todo = sys.argv[1:] or ["all"]
    for s in (list(steps) if todo == ["all"] else todo):
        steps[s]()
