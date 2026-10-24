"""Download Karnataka datasets from the National Water Data Portal (nwdp.nwic.gov.in, NWIC / Ministry of Jal Shakti).

    python train/fetch_nwdp.py            # all datasets below
    python train/fetch_nwdp.py reservoirs # just one

The portal is CKAN: each resource has a full CSV dump at /datastore/dump/<resource_id>. Files land in
data/_downloads/nwdp/ (git-ignored, ~150 MB); the cleaning scripts write compact outputs to data/karnataka/.
"""
import sys
from pathlib import Path

import httpx

DL = Path(__file__).resolve().parent.parent / "data" / "_downloads" / "nwdp"
DUMP = "https://nwdp.nwic.gov.in/datastore/dump/{}"

RESOURCES = {
    "reservoirs": {"reservoirs_daily_1990-2026": "26800982-045c-41de-821d-b1ca080a79a8"},
    "groundwater": {
        "gwl_monthly_1971-2020": "00ee62df-76d2-4431-85dd-a5da3bfc36f0",
        "gwl_monthly_2021-2025": "ac075bf0-3894-4387-89c7-ae242f2cb060",
        "gwl_monthly_2026-2030": "4e393536-9a75-4ae8-a246-64a2530e16a9",
    },
    "tanks": {"minor_irrigation_tanks": "52dc620d-5020-4885-a870-cd6d26064f3b"},
    "discharge": {
        "discharge_daily_1972-2020": "a21e8e48-d5e3-4a35-8274-007e52f92daf",
        "discharge_daily_2021-2025": "d1bf65de-1010-47e5-beb6-23ff7ac82888",
    },
}


def fetch(name, rid):
    path = DL / f"{name}.csv"
    if path.exists() and path.stat().st_size > 0:
        print(f"  {path.name} already downloaded")
        return
    tmp = path.with_suffix(".part")
    for attempt in range(4):
        try:
            with httpx.stream("GET", DUMP.format(rid), timeout=httpx.Timeout(60, read=600), follow_redirects=True) as r:
                r.raise_for_status()
                with open(tmp, "wb") as f:
                    for chunk in r.iter_bytes():
                        f.write(chunk)
            tmp.replace(path)
            print(f"  {path.name}: {path.stat().st_size / 1e6:.1f} MB")
            return
        except httpx.HTTPError as e:
            print(f"  {name}: {e!r}, retry {attempt + 1}")
    raise RuntimeError(f"could not download {name}")


if __name__ == "__main__":
    DL.mkdir(parents=True, exist_ok=True)
    for group in sys.argv[1:] or list(RESOURCES):
        print(group)
        for name, rid in RESOURCES[group].items():
            fetch(name, rid)
