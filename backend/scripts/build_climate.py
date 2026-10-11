"""Builds app/data/climate.json: typical weather for every destination, month by month.

Averages six years (2019–2024) of real daily weather from the Open-Meteo historical API (free,
no key). Run again only when cities are added:

    .venv/Scripts/python scripts/build_climate.py
"""

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import httpx

DATA = Path(__file__).resolve().parents[1] / "app" / "data"
URL = "https://archive-api.open-meteo.com/v1/archive"
START, END = "2019-01-01", "2024-12-31"
RAINY_DAY_MM = 2.5  # India Meteorological Department's definition of a rainy day
YEARS = 6


def monthly(daily: dict) -> list[dict]:
    by_month: dict[int, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for day, hi, lo, rain in zip(daily["time"], daily["temperature_2m_max"], daily["temperature_2m_min"], daily["precipitation_sum"]):
        if hi is None or lo is None or rain is None:
            continue
        m = by_month[int(day[5:7])]
        m["hi"].append(hi)
        m["lo"].append(lo)
        m["rain"].append(rain)
    out = []
    for month in range(1, 13):
        m = by_month[month]
        out.append({
            "month": month,
            "tmax": round(sum(m["hi"]) / len(m["hi"]), 1),
            "tmin": round(sum(m["lo"]) / len(m["lo"]), 1),
            "rain_mm": round(sum(m["rain"]) / YEARS),
            "rainy_days": round(sum(r >= RAINY_DAY_MM for r in m["rain"]) / YEARS, 1),
        })
    return out


def main() -> None:
    cities = json.loads((DATA / "cities.json").read_text(encoding="utf-8"))
    path = DATA / "climate.json"
    result = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    with httpx.Client(timeout=60) as client:
        for c in cities:
            if c["name"] in result:
                continue  # already fetched (lets a rate-limited run resume)
            params = {"latitude": c["lat"], "longitude": c["lng"], "start_date": START, "end_date": END,
                      "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum", "timezone": "auto"}
            for attempt in range(5):
                r = client.get(URL, params=params)
                if r.status_code != 429:
                    break
                time.sleep(30 * (attempt + 1))  # free tier is rate limited; wait and retry
            r.raise_for_status()
            result[c["name"]] = monthly(r.json()["daily"])
            path.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            print(f"{c['name']}: done", flush=True)
            time.sleep(1.5)
    print(f"{len(result)} destinations in {path}", file=sys.stderr)


if __name__ == "__main__":
    main()
