"""
Step 1: Fetch earthquake data from the USGS API (last 5 years, month by month).

Why two formats?
- format=geojson gives: mag, place, time, updated, tsunami, sig, alert, ids, sources, types, ...
- format=csv gives the quality fields geojson leaves out: magError, depthError, magNst,
  locationSource, magSource.
We fetch both for each month and merge them on the event id, so we get all 26 features.
"""
import io
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import pandas as pd
import requests
import urllib3.util.connection

# Some networks hang on IPv6 connections to USGS: force IPv4
urllib3.util.connection.allowed_gai_family = lambda: socket.AF_INET

API_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
START = date(2021, 11, 1)   # 5 years of data
END = date(2026, 11, 1)
MIN_MAGNITUDE = 4.5         # M4.5+ = globally well-recorded, felt earthquakes
OUTPUT = "data/raw_earthquakes.csv"


def month_ranges(start, end):
    """Yield (start_date, end_date) for every month between start and end."""
    current = start
    while current < end:
        nxt = date(current.year + (current.month == 12), current.month % 12 + 1, 1)
        yield current, min(nxt, end)
        current = nxt


def get_with_retry(params, retries=5):
    """Call the API; retry if the request fails or the status code is not 200."""
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(API_URL, params=params, timeout=(10, 90))
            if response.status_code == 200:
                return response
            print(f"  status {response.status_code}, attempt {attempt}")
        except requests.RequestException as error:
            print(f"  error: {error}, attempt {attempt}")
        time.sleep(2 * attempt)
    raise RuntimeError(f"Failed after {retries} attempts: {params}")


def fetch_month(start, end):
    base = {"starttime": start.isoformat(), "endtime": end.isoformat(),
            "minmagnitude": MIN_MAGNITUDE, "orderby": "time-asc"}

    # 1) GeoJSON -> list of dictionaries (properties + geometry)
    features = get_with_retry({**base, "format": "geojson"}).json()["features"]
    records = []
    for f in features:
        p = f["properties"]
        lon, lat, depth = f["geometry"]["coordinates"]
        records.append({
            "id": f["id"], "time": p["time"], "updated": p["updated"],
            "latitude": lat, "longitude": lon, "depth_km": depth,
            "mag": p["mag"], "magType": p["magType"], "place": p["place"],
            "status": p["status"], "tsunami": p["tsunami"], "sig": p["sig"],
            "net": p["net"], "nst": p["nst"], "dmin": p["dmin"], "rms": p["rms"],
            "gap": p["gap"], "types": p["types"], "ids": p["ids"],
            "sources": p["sources"], "type": p["type"], "alert": p["alert"],
            "felt": p["felt"], "cdi": p["cdi"], "mmi": p["mmi"],
        })
    geo = pd.DataFrame(records)
    if geo.empty:
        return geo

    # 2) CSV -> quality columns, merged on id
    csv_text = get_with_retry({**base, "format": "csv"}).text
    quality = pd.read_csv(io.StringIO(csv_text))[
        ["id", "magError", "depthError", "magNst", "locationSource", "magSource"]]
    return geo.merge(quality, on="id", how="left")


def main():
    months = list(month_ranges(START, END))
    # Fetch 6 months at a time in parallel (pool.map keeps the original month order)
    with ThreadPoolExecutor(max_workers=6) as pool:
        frames = list(pool.map(lambda m: fetch_month(*m), months))
    for (start, _), month_df in zip(months, frames):
        print(f"{start:%Y-%m}: {len(month_df)} earthquakes")

    df = pd.concat(frames, ignore_index=True)

    # Timestamps come in milliseconds since 1970 -> convert to datetime (UTC)
    df["time"] = pd.to_datetime(df["time"], unit="ms")
    df["updated"] = pd.to_datetime(df["updated"], unit="ms")

    print("\nShape:", df.shape)
    print(df.head())
    print(df.dtypes)
    df.to_csv(OUTPUT, index=False)
    print(f"\nSaved {OUTPUT}")


if __name__ == "__main__":
    main()
