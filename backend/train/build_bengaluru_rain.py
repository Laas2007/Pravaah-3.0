"""Rebuild data/rainfall.json (input of the Bengaluru ward model, backend/model.py) from IMD rain gauges.

    python train/build_bengaluru_rain.py        (needs the IMD yearly files: python train/fetch_karnataka.py imd)

Before: daily ERA5 reanalysis (Open-Meteo) at 16 city points + 2 Cauvery catchment points. ERA5 under-counts
Bengaluru's wet years badly (2022: ~1,200 vs ~1,700 mm at IMD), so the ward model's rain was not authentic.
After:  IMD 0.25 deg gauge-based daily grid, bilinearly interpolated to the same 18 points, 2014-2025.
        Cells with missing gauge reports (e.g. east Bengaluru in 2024) are filled from their neighbours first
        (spatial-consistency QC in train/imd_qc.py).
        After IMD's last published year, ERA5 is scaled by the point's IMD/ERA5 ratio for that calendar month.
The original ERA5 file is kept as data/_downloads/rainfall_era5.json for the comparison printed at the end.
"""
import datetime as dt
import json
import shutil
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_karnataka import IMD_YEARS, imd_year  # noqa: E402
from imd_qc import IMD_LAT, IMD_LON, REGION, qc  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data"
RAIN = DATA / "rainfall.json"
ERA5_COPY = DATA / "_downloads" / "rainfall_era5.json"


def bilinear(a, lat, lon):
    """Daily series at (lat, lon) from (days, IMD_LAT, IMD_LON) grid a."""
    i = np.searchsorted(IMD_LAT, lat) - 1
    j = np.searchsorted(IMD_LON, lon) - 1
    fy = (lat - IMD_LAT[i]) / 0.25
    fx = (lon - IMD_LON[j]) / 0.25
    c = [a[:, i, j], a[:, i, j + 1], a[:, i + 1, j], a[:, i + 1, j + 1]]
    w = np.array([(1 - fy) * (1 - fx), (1 - fy) * fx, fy * (1 - fx), fy * fx])
    vals = np.stack(c)
    ok = np.isfinite(vals)
    return np.nansum(vals * w[:, None], axis=0) / np.maximum((ok * w[:, None]).sum(axis=0), 1e-9)


def main():
    if not ERA5_COPY.exists():
        shutil.copy(RAIN, ERA5_COPY)
    era = json.loads(ERA5_COPY.read_text())
    dates = era["dates"]
    pts = [(p["lat"], p["lon"]) for p in era["city_grid"]]
    catch_pts = {"kodagu_krs": (12.42, 75.74), "wayanad_kabini": (11.70, 76.10)}
    allpts = pts + list(catch_pts.values())

    i0, i1, j0, j1 = REGION
    years, imd_dates = {}, []
    for y in IMD_YEARS:
        a = imd_year(y).astype(np.float64)
        a[a < -900] = np.nan
        years[y] = a[:, i0:i1, j0:j1].copy()
        imd_dates += [(dt.date(y, 1, 1) + dt.timedelta(days=k)).isoformat() for k in range(a.shape[0])]
    m_fix, y_fix, y_list = qc(years)
    full = np.full((1, len(IMD_LAT), len(IMD_LON)), np.nan)
    series = [[] for _ in allpts]
    for y in IMD_YEARS:
        g = np.repeat(full, years[y].shape[0], axis=0)
        g[:, i0:i1, j0:j1] = years[y]
        for n, (la, lo) in enumerate(allpts):
            series[n].append(bilinear(g, la, lo))
    imd = np.array([np.concatenate(s) for s in series])                    # (points, imd days)
    print(f"IMD {imd_dates[0]}..{imd_dates[-1]}: QC filled {y_fix} cell-years and {m_fix} cell-months (see imd_qc.py)")
    print("  cell-years:", y_list)

    # ERA5 series for the same points
    era_arr = np.array([p["rain"] for p in era["city_grid"]] + [era["catchment"][k] for k in catch_pts])
    assert dates[0] == imd_dates[0]
    n_imd = len(imd_dates)
    cal = np.array([int(d[5:7]) for d in dates])
    ratio = np.ones((len(allpts), 12))
    for mo in range(1, 13):
        s = cal[:n_imd] == mo
        ratio[:, mo - 1] = np.clip(imd[:, s].sum(1) / np.maximum(era_arr[:, :n_imd][:, s].sum(1), 1), 0.3, 3.0)
    tail = era_arr[:, n_imd:] * ratio[:, cal[n_imd:] - 1]
    rain = np.concatenate([imd, tail], axis=1)
    rain = np.round(np.clip(rain, 0, None), 2)

    out = {
        "source": "IMD 0.25 deg gridded daily rainfall (rain-gauge based), QC-filled (train/imd_qc.py), bilinear to each point; "
                  f"after {imd_dates[-1]}: ERA5 (Open-Meteo) scaled by the point's monthly IMD/ERA5 ratio. mm/day",
        "fetched": dt.date.today().isoformat(), "rain_source_imd_until": imd_dates[-1], "dates": dates,
        "city_grid": [{"lat": la, "lon": lo, "rain": rain[n].tolist()} for n, (la, lo) in enumerate(pts)],
        "catchment": {k: rain[len(pts) + n].tolist() for n, k in enumerate(catch_pts)},
    }
    RAIN.write_text(json.dumps(out))
    print(f"wrote {RAIN.name}: {len(dates)} days, IMD until {imd_dates[-1]}")

    yrs = sorted({d[:4] for d in dates[:n_imd]})
    print("\nBengaluru city mean annual rain (mm):  year  ERA5  IMD(new)")
    for y in yrs:
        s = np.array([d[:4] == y for d in dates])
        print(f"   {y}  {era_arr[:16, s].sum(1).mean():6.0f}  {rain[:16, s].sum(1).mean():6.0f}")
    s = np.array([d[:4] in yrs for d in dates])
    print("Cauvery catchment (Kodagu, Wayanad) mean annual, ERA5 vs IMD:",
          [f"{era_arr[16 + n, s].sum() / len(yrs):.0f} vs {rain[16 + n, s].sum() / len(yrs):.0f}" for n in range(2)])


if __name__ == "__main__":
    main()
