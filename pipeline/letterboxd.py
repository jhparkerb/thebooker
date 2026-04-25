"""
Letterboxd data access — watchlist and watched-list for a given username.

Two sources supported:
  1. HTML scraping of letterboxd.com (watchlist only; gentle, cached weekly)
  2. CSV export from LB Settings → Data → Export (preferred for watched list)

Letterboxd grid HTML structure (as of 2026):
  <li class="griditem">
    <div class="react-component" data-component-class="LazyPoster"
         data-item-name="Some Film (2026)"
         data-item-slug="some-film" ...>
"""

from __future__ import annotations
import csv
import json
import re
import time
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

CACHE_PATH = Path(__file__).parent.parent / "pipeline" / "cache" / "letterboxd.json"
BASE_URL   = "https://letterboxd.com"
HEADERS    = {
    "User-Agent": "TheBooker/1.0 (personal movie scheduling tool; non-commercial)",
    "Accept-Language": "en-US,en;q=0.9",
}
WATCHLIST_TTL_SECS = 7  * 86400   # re-fetch watchlist weekly
WATCHED_TTL_SECS   = 30 * 86400   # re-fetch watched monthly (barely changes)


# ---------------------------------------------------------------------------
# HTML parser — extracts film slugs + titles from poster-list pages
# ---------------------------------------------------------------------------

class _PosterParser(HTMLParser):
    """
    Parses Letterboxd grid pages. Each film entry looks like:
      <li class="griditem">
        <div class="react-component" data-component-class="LazyPoster"
             data-item-name="Coyote vs. ACME (2026)"
             data-item-slug="coyote-vs-acme" ...>
    """
    def __init__(self):
        super().__init__()
        self.films: list[dict] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "div":
            return
        d = dict(attrs)
        if d.get("data-component-class") != "LazyPoster":
            return
        display_name = d.get("data-item-name", "") or d.get("data-item-full-display-name", "")
        slug = d.get("data-item-slug", "")
        title, year = _parse_display_name(display_name)
        if slug or title:
            self.films.append({"slug": slug, "title": title, "year": year})


def _parse_display_name(name: str) -> tuple[str, int | None]:
    """'Coyote vs. ACME (2026)' → ('Coyote vs. ACME', 2026)"""
    m = re.match(r"^(.*?)\s+\((\d{4})\)\s*$", name)
    if m:
        return m.group(1).strip(), int(m.group(2))
    return name.strip(), None


def _fetch_page(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _has_next_page(html: str, current: int) -> bool:
    return f'href="?page={current + 1}"' in html or \
           f'/page/{current + 1}/' in html


def _scrape_list(url_template: str, max_pages: int = 200,
                  stop_before_year: int | None = None) -> list[dict]:
    """Paginate a poster-list URL. url_template must contain {page}.

    If stop_before_year is set, stop after a page that contains no films
    from that year or later — keeps upcoming-only scrapes very short.
    """
    films: list[dict] = []
    for page in range(1, max_pages + 1):
        html = _fetch_page(url_template.format(page=page))
        parser = _PosterParser()
        parser.feed(html)
        if not parser.films:
            break
        films.extend(parser.films)
        if stop_before_year is not None:
            recent = [f for f in parser.films
                      if f["year"] is not None and f["year"] >= stop_before_year]
            if not recent:
                break   # no upcoming films on this page — we're past the horizon
        if not _has_next_page(html, page):
            break
        time.sleep(2.0)  # gentle — 2s between page requests
    return films


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _load_cache() -> dict:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text())
    return {}


def _save_cache(cache: dict) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2))


def fetch_watchlist(username: str, force: bool = False,
                    upcoming_only: bool = True,
                    min_year: int = 2025) -> list[dict]:
    """
    Return {slug, title, year} dicts from the user's LB watchlist.

    upcoming_only=True (default): stop paginating once a page contains no
    films from min_year or later. This keeps the scrape very small (typically
    10-15 pages) and targets films that might actually be playing in theaters.
    Set upcoming_only=False to fetch the full watchlist.
    """
    return _fetch_cached(username, "watchlist",
                         f"{BASE_URL}/{username}/watchlist/page/{{page}}/",
                         force, WATCHLIST_TTL_SECS,
                         stop_before_year=min_year if upcoming_only else None)


def fetch_watched(username: str, csv_path: Path | None = None,
                  force: bool = False) -> list[dict]:
    """Return {slug, title, year} dicts for the user's watched films.

    Prefer csv_path (LB Settings → Data → Export → watched.csv) — it's
    complete, instant, and puts zero load on letterboxd.com.
    Falls back to HTML scraping if no CSV is provided, but that's slow for
    large libraries (~3-5 min) and should only run once (cached 30 days).
    """
    if csv_path is not None:
        return _read_watched_csv(csv_path)
    return _fetch_cached(username, "watched",
                         f"{BASE_URL}/{username}/films/page/{{page}}/",
                         force, WATCHED_TTL_SECS)


def _read_watched_csv(csv_path: Path) -> list[dict]:
    """Parse LB's watched.csv export. Columns: Date,Name,Year,Letterboxd URI,Rating"""
    films = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            title = row.get("Name", "").strip()
            year_str = row.get("Year", "").strip()
            slug = row.get("Letterboxd URI", "").rstrip("/").split("/")[-1]
            if title:
                films.append({
                    "slug":  slug,
                    "title": title,
                    "year":  int(year_str) if year_str.isdigit() else None,
                })
    return films


def _fetch_cached(username: str, list_name: str,
                  url_template: str, force: bool, ttl: int,
                  stop_before_year: int | None = None) -> list[dict]:
    cache = _load_cache()
    key = f"{username}:{list_name}"
    now = time.time()
    if not force and key in cache:
        entry = cache[key]
        if now - entry["cached_at"] < ttl:
            return entry["films"]

    print(f"[letterboxd] fetching {list_name} for {username}...")
    films = _scrape_list(url_template, stop_before_year=stop_before_year)
    cache[key] = {"cached_at": now, "films": films}
    _save_cache(cache)
    print(f"[letterboxd] {len(films)} films in {list_name}")
    return films
