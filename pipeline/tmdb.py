"""
TMDB API client — title/genre lookup with local JSON cache.
Cache TTL defaults to config.yaml tmdb.cache_ttl_days (max 180 per ToS).
"""

from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any

import urllib.request
import urllib.parse

CACHE_PATH = Path(__file__).parent.parent / "pipeline" / "cache" / "tmdb.json"
API_BASE   = "https://api.themoviedb.org/3"
HORROR_GENRE_ID = 27


def _load_cache() -> dict:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text())
    return {}


def _save_cache(cache: dict) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2))


def _get(path: str, token: str, params: dict | None = None) -> Any:
    url = API_BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    })
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2 ** attempt)
                continue
            raise
    raise RuntimeError(f"TMDB rate limit persists after retries: {path}")


def lookup(title: str, year: int | None, token: str,
           ttl_days: int = 180) -> dict | None:
    """
    Return a dict with keys: tmdb_id, canonical_title, year, is_horror, genres.
    Returns None if no match found.
    Results are cached locally.
    """
    cache_key = f"{title}|{year}"
    cache = _load_cache()
    now = time.time()
    ttl_secs = ttl_days * 86400

    if cache_key in cache:
        entry = cache[cache_key]
        if now - entry["cached_at"] < ttl_secs:
            return entry["data"]

    params: dict = {"query": title, "include_adult": "false"}
    if year:
        params["year"] = year

    try:
        results = _get("/search/movie", token, params).get("results", [])
    except Exception as e:
        print(f"[tmdb] search failed for {title!r}: {e}")
        return None

    if not results:
        # Retry without year constraint
        if year:
            try:
                results = _get("/search/movie", token,
                               {"query": title, "include_adult": "false"}).get("results", [])
            except Exception:
                return None

    if not results:
        data = None
    else:
        r = results[0]
        genre_ids: list[int] = r.get("genre_ids", [])
        release_year = int(r["release_date"][:4]) if r.get("release_date") else None

        # Fetch keywords (one extra call, but result is cached together)
        keywords: list[str] = []
        try:
            kw_resp = _get(f"/movie/{r['id']}/keywords", token)
            keywords = [k["name"].lower() for k in kw_resp.get("keywords", [])]
        except Exception:
            pass

        data = {
            "tmdb_id":           r["id"],
            "canonical_title":   r["title"],
            "year":              release_year,
            "is_horror":         HORROR_GENRE_ID in genre_ids,
            "genres":            genre_ids,
            "original_language": r.get("original_language", "en"),
            "keywords":          keywords,
        }

    cache[cache_key] = {"cached_at": now, "data": data}
    _save_cache(cache)
    return data


def bulk_lookup(titles: list[tuple[str, int | None]], token: str,
                ttl_days: int = 180) -> dict[tuple, dict | None]:
    """
    Look up a list of (title, year) pairs. Returns a dict keyed by (title, year).
    Skips titles already in cache to avoid redundant API calls.
    """
    return {(t, y): lookup(t, y, token, ttl_days) for t, y in titles}
