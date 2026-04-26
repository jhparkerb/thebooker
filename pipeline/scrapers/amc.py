"""
AMC showtimes scraper — uses the official AMC catalog API.
Vendor key is in config.yaml under amc.vendor_key.

Key endpoints:
  GET /ams/v2/theatres?searchText=...          find theater IDs
  GET /ams/v2/theatres/{id}/showtimes/{date}   get a day's showings

Response format per showtime (relevant fields):
  movieName, showDateTimeLocal, runTime,
  attributes: [{code, name}]  — includes IMAX, PRIME, DOLBY, etc.
  seatMapAvailable (proxy for reserved/recliner seating)

Raw responses are cached per (theater_id, date) to avoid redundant calls.
"""

from __future__ import annotations
import json
import time
import urllib.request
import urllib.parse
from datetime import date
from pathlib import Path

import yaml

from pipeline.optimizer import Showing
from pipeline.scrapers.base import Scraper

API_BASE   = "https://api.amctheatres.com/ams/v2"
CACHE_DIR  = Path(__file__).parent.parent / "cache" / "amc"
CONFIG     = Path(__file__).parent.parent.parent / "config.yaml"

# AMC attribute codes that map to our format/recliner fields
FORMAT_CODES = {
    "IMAX":       "IMAX",
    "PRIME":      "PRIME",
    "DOLBY":      "DOLBY",
    "PLF":        "IMAX",    # Premium Large Format (treat as IMAX)
    "3D":         "3D",
}
RECLINER_CODES = {"RESERVE", "RECLINE", "DINE-IN", "PRIME", "DOLBY"}


_cfg_cache: dict | None = None

def _cfg() -> dict:
    global _cfg_cache
    if _cfg_cache is None:
        _cfg_cache = yaml.safe_load(CONFIG.read_text())
    return _cfg_cache


def _headers() -> dict:
    return {
        "X-AMC-Vendor-Key": _cfg()["amc"]["vendor_key"],
        "Accept": "application/json",
        "User-Agent": "TheBooker/1.0 (personal scheduling tool; non-commercial)",
    }


def _get(path: str, params: dict | None = None) -> dict:
    url = API_BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=_headers())
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2 ** attempt)
                continue
            raise
    raise RuntimeError(f"AMC API rate limit persists: {path}")


def find_theater_id(search_text: str) -> list[dict]:
    """Search for theaters by name. Returns list of {id, name, slug}."""
    data = _get("/theatres", {"pageSize": 20, "searchText": search_text})
    return [
        {"id": t["id"], "name": t["name"], "slug": t.get("slug", "")}
        for t in data.get("_embedded", {}).get("theatres", [])
    ]


def _cache_path(theater_id: str, day: date) -> Path:
    return CACHE_DIR / f"{theater_id}_{day.isoformat()}.json"


def _parse_time(dt_str: str) -> int:
    """'2026-04-25T14:30:00' → minutes from midnight (870)"""
    t = dt_str[11:16]   # 'HH:MM'
    h, m = int(t[:2]), int(t[3:5])
    return h * 60 + m


def _parse_format_recliner(attributes: list[dict]) -> tuple[str, bool]:
    fmt = "STANDARD"
    recliner = False
    for attr in attributes:
        code = attr.get("code", "").upper()
        if code in FORMAT_CODES:
            fmt = FORMAT_CODES[code]
        if code in RECLINER_CODES:
            recliner = True
    return fmt, recliner


def fetch_raw(theater_id: str, day: date, force: bool = False) -> dict:
    """Fetch (and cache) the raw API response for one theater/day."""
    path = _cache_path(theater_id, day)
    if not force and path.exists():
        return json.loads(path.read_text())
    data = _get(f"/theatres/{theater_id}/showtimes/{day.isoformat()}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))
    return data


class AMCScraper(Scraper):
    def __init__(self, theater_id: str, theater_name: str):
        self.theater_id   = theater_id
        self.theater_name = theater_name

    def fetch(self, theater_id: str, day: date) -> list[Showing]:
        raw = fetch_raw(theater_id, day)
        showings: list[Showing] = []

        for movie in raw.get("_embedded", {}).get("showtimes", []):
            title = movie.get("movieName", "").strip()
            runtime = movie.get("runTime") or 0
            if not title or not runtime:
                continue

            for showtime in movie.get("showDateTimes", [movie]):
                dt_str = showtime.get("showDateTimeLocal", "")
                if not dt_str:
                    continue
                start_min = _parse_time(dt_str)
                attrs = showtime.get("attributes", [])
                fmt, recliner = _parse_format_recliner(attrs)

                showings.append(Showing(
                    title_raw        = title,
                    title_canonical  = title,
                    tmdb_id          = None,
                    year             = None,
                    theater_id       = theater_id,
                    day              = day,
                    listed_start_min = start_min,
                    runtime_min      = runtime,
                    format           = fmt,
                    has_recliner     = recliner,
                ))
        return showings


# ---------------------------------------------------------------------------
# CLI helper: python -m pipeline.scrapers.amc --test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    cfg = _cfg()
    theater_cfg = next(t for t in cfg["theaters"] if t["chain"] == "amc")

    if "--find" in sys.argv:
        results = find_theater_id("waterfront")
        for r in results:
            print(f"  id={r['id']}  name={r['name']!r}  slug={r['slug']!r}")
        sys.exit(0)

    # Default: fetch today + tomorrow
    today = date.today()
    theater_id = theater_cfg["chain_id"]
    scraper = AMCScraper(theater_id, theater_cfg["name"])

    for offset in range(2):
        day = today + timedelta(days=offset)
        try:
            showings = scraper.fetch(theater_id, day)
            print(f"\n{day}  ({len(showings)} showings)")
            for s in sorted(showings, key=lambda x: x.listed_start_min)[:8]:
                h, m = divmod(s.listed_start_min, 60)
                ap = "pm" if h >= 12 else "am"
                print(f"  {h%12 or 12}:{m:02d}{ap}  {s.title_raw:<40} {s.format}  {'recliner' if s.has_recliner else ''}")
        except Exception as e:
            print(f"{day}: {e}")
