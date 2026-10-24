"""Download the real input data used by the model.

Rainfall: daily precipitation from the Open-Meteo historical archive (ERA5 /
ERA5-Land reanalysis), on a 0.1 degree grid over Bengaluru plus two points in
the Cauvery catchment (Kodagu -> KRS, Wayanad -> Kabini) that feed the city's
piped supply.

Run once (re-run to refresh):  python fetch_data.py
"""
import datetime as dt
import json
from pathlib import Path

import httpx

DATA = Path(__file__).parent / "data"
START = "2014-01-01"

CITY_LATS = [12.85, 12.95, 13.05, 13.15]
CITY_LONS = [77.45, 77.55, 77.65, 77.75]
CATCHMENT = {"kodagu_krs": (12.42, 75.74), "wayanad_kabini": (11.70, 76.10)}


def fetch(points, end):
    lats = ",".join(str(p[0]) for p in points)
    lons = ",".join(str(p[1]) for p in points)
    r = httpx.get(
        "https://archive-api.open-meteo.com/v1/archive",
        params={
            "latitude": lats,
            "longitude": lons,
            "start_date": START,
            "end_date": end,
            "daily": "precipitation_sum",
            "timezone": "Asia/Kolkata",
        },
        timeout=120,
    )
    r.raise_for_status()
    body = r.json()
    return body if isinstance(body, list) else [body]


def main():
    # The archive lags real time by a few days.
    end = (dt.date.today() - dt.timedelta(days=6)).isoformat()
    city_pts = [(la, lo) for la in CITY_LATS for lo in CITY_LONS]
    city = fetch(city_pts, end)
    catch = fetch(list(CATCHMENT.values()), end)

    def clean(v):
        return [0.0 if x is None else float(x) for x in v]

    out = {
        "source": "Open-Meteo historical weather archive (ERA5 reanalysis), daily precipitation_sum, mm",
        "fetched": dt.date.today().isoformat(),
        "dates": city[0]["daily"]["time"],
        "city_grid": [
            {"lat": p[0], "lon": p[1], "rain": clean(b["daily"]["precipitation_sum"])}
            for p, b in zip(city_pts, city)
        ],
        "catchment": {
            name: clean(b["daily"]["precipitation_sum"])
            for name, b in zip(CATCHMENT, catch)
        },
    }
    (DATA / "rainfall.json").write_text(json.dumps(out))
    print(f"saved {len(out['dates'])} days x {len(city_pts)} city points, {out['dates'][0]} .. {out['dates'][-1]}")


if __name__ == "__main__":
    main()
