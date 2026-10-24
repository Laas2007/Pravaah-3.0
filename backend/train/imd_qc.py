"""Quality control for the IMD 0.25 deg gridded rainfall (shared by the rain build scripts).

IMD's grid is interpolated from rain gauges; when a gauge stops reporting, its cell can read far too low (e.g. the
cell east of Bengaluru, 13.0N 77.75E, got 396 mm in 2024 while its neighbours got ~730 mm although it is normally
16 % wetter than them). Two spatial-consistency checks, applied only around Karnataka (REGION):

  month: a cell-month with < 25 % of its neighbours' median (> 40 mm) is a gap, if the cell is normally similar to its
         neighbours in that calendar month (median ratio over all years > 0.6);
  year:  a cell-year with < 60 % of its neighbours' median annual total (> 300 mm) is a gap, if the cell normally gets
         > 85 % of its neighbours (typical annual ratio).
Gaps get the neighbours' mean daily rain scaled by the cell's typical ratio. Naturally drier cells (rain shadows)
fail the "normally similar" test and are left alone. Around Karnataka this touches ~60 cell-months and ~14 cell-years.
"""
import datetime as dt
import warnings

import numpy as np

IMD_LAT = 6.5 + 0.25 * np.arange(129)
IMD_LON = 66.5 + 0.25 * np.arange(135)
REGION = (int(np.searchsorted(IMD_LAT, 10.0)), int(np.searchsorted(IMD_LAT, 15.0)),
          int(np.searchsorted(IMD_LON, 74.0)), int(np.searchsorted(IMD_LON, 79.0)))
RING = [(di, dj) for di in (-1, 0, 1) for dj in (-1, 0, 1) if di or dj]


def neighbour_median(tot):
    """tot: (..., lat, lon) -> median of the 8 neighbours (NaN at edges / sea, or with < 4 valid neighbours)."""
    nb = np.full(tot.shape, np.nan)
    for i in range(1, tot.shape[-2] - 1):
        for j in range(1, tot.shape[-1] - 1):
            ring = np.stack([tot[..., i + di, j + dj] for di, dj in RING], axis=-1)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                nb[..., i, j] = np.where(np.isfinite(ring).sum(-1) >= 4, np.nanmedian(ring, axis=-1), np.nan)
    return nb


def _ring_mean(a, sel, i, j):
    return np.nanmean(np.stack([a[sel, i + di, j + dj] for di, dj in RING]), axis=0)


def qc(years):
    """years: {year: (days, lat, lon) array cropped to REGION, NaN = no data}. Fixed in place.
    Returns (month_fixes, year_fixes, [(year, lat, lon), ...] for the year fixes)."""
    ys = sorted(years)
    shape = years[ys[0]].shape[1:]
    month_of = {y: np.array([(dt.date(y, 1, 1) + dt.timedelta(days=k)).month for k in range(years[y].shape[0])])
                for y in ys}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        # year check first (whole-year gauge problems), then month check on the result
        ann = np.array([np.where(np.isnan(years[y][0]), np.nan, np.nansum(years[y], axis=0)) for y in ys])
        nb_a = neighbour_median(ann)
        r_a = np.where(nb_a > 300, ann / nb_a, np.nan)
        typ_a = np.nanmedian(r_a, axis=0)
        bad_y = (nb_a > 300) & (r_a < 0.6) & (typ_a[None] > 0.85)
        year_list = []
        for n, y in enumerate(ys):
            for i, j in zip(*np.where(bad_y[n])):
                sel = np.ones(years[y].shape[0], bool)
                years[y][:, i, j] = _ring_mean(years[y], sel, i, j) * typ_a[i, j]
                year_list.append((y, float(IMD_LAT[REGION[0] + i]), float(IMD_LON[REGION[2] + j])))

        tot = np.full((len(ys), 12) + shape, np.nan)
        for n, y in enumerate(ys):
            for mo in range(1, 13):
                s = month_of[y] == mo
                tot[n, mo - 1] = np.where(np.isnan(years[y][0]), np.nan, np.nansum(years[y][s], axis=0))
        nb = neighbour_median(tot)
        ratio = np.where(nb > 40, tot / nb, np.nan)
        typ = np.nanmedian(ratio, axis=0)
        gaps = (nb > 40) & (tot < 0.25 * nb) & (typ[None] > 0.6)
        for n, y in enumerate(ys):
            for mo in range(1, 13):
                s = month_of[y] == mo
                for i, j in zip(*np.where(gaps[n, mo - 1])):
                    years[y][s, i, j] = _ring_mean(years[y], s, i, j) * typ[mo - 1, i, j]
    return int(gaps.sum()), len(year_list), year_list
