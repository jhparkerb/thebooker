"""
Builds TagSets from Letterboxd lists + TMDB genre/language data + rule overrides.

Resolution order (highest priority first):
  1. force_skip TMDB ids in overrides.yaml
  2. LB watchlist  → always un-skipped; must_see bonus
  3. LB watched    → skip
  4. auto_skip rules (genre, language, runtime)
  5. TMDB horror genre → horror bonus
  6. everything else   → would_see (implicitly, any un-skipped showing)
"""

from __future__ import annotations
from pathlib import Path
from typing import Any

import yaml

from pipeline.optimizer import TagSets
from pipeline.tmdb import lookup as tmdb_lookup
from pipeline.letterboxd import fetch_watchlist, fetch_watched

OVERRIDES_PATH    = Path(__file__).parent.parent / "overrides.yaml"
TMDB_HORROR_GENRE = 27


def _load_overrides() -> dict:
    if not OVERRIDES_PATH.exists():
        return {}
    return yaml.safe_load(OVERRIDES_PATH.read_text()) or {}


def _resolve_lb_to_tmdb(films: list[dict], token: str, ttl_days: int) -> dict[int, dict]:
    """Map TMDB id → result dict for every LB film we can resolve.
    Skips the TMDB lookup when the LB entry already carries a tmdb_id
    (the watched RSS feed bundles it)."""
    resolved: dict[int, dict] = {}
    for f in films:
        if f.get("tmdb_id"):
            resolved[f["tmdb_id"]] = f
            continue
        r = tmdb_lookup(f["title"], f["year"], token, ttl_days)
        if r:
            resolved[r["tmdb_id"]] = r
    return resolved


def _should_auto_skip(result: dict, rules: dict, watchlist_ids: set[int]) -> bool:
    """Return True if this TMDB result should be auto-skipped per override rules."""
    if result["tmdb_id"] in watchlist_ids:
        return False   # watchlist always overrides auto-skip
    genre_ids = result.get("genres", [])
    skip_genres = set(rules.get("genres", []))
    if skip_genres & set(genre_ids):
        return True
    skip_langs = set(rules.get("skip_languages", []))
    if skip_langs:
        lang = result.get("original_language", "en")
        if lang in skip_langs:
            return True

    skip_keywords = [k.lower() for k in rules.get("skip_keywords", [])]
    if skip_keywords:
        film_keywords = result.get("keywords", [])
        if any(sk in fk for sk in skip_keywords for fk in film_keywords):
            return True

    return False


def build_tag_sets(
    cfg: dict[str, Any],
    showings: list[tuple[str, int | None]],   # (title_raw, year) pairs currently playing
) -> TagSets:
    """
    Build TagSets for the titles currently showing.
    Only the showing titles are looked up on TMDB (not the full LB lists) —
    LB lists are resolved lazily as well, but cached aggressively.
    """
    token    = cfg["tmdb"]["read_access_token"]
    ttl_days = cfg["tmdb"].get("cache_ttl_days", 180)
    lb_user  = cfg["letterboxd"]["username"]

    overrides  = _load_overrides()
    auto_rules = overrides.get("auto_skip", {})

    force_skip = set(overrides.get("force_skip_tmdb_ids", []))

    # --- Resolve LB lists to TMDB ids ---
    lb_watchlist = fetch_watchlist(lb_user)
    lb_watched   = fetch_watched(lb_user)

    watchlist_resolved = _resolve_lb_to_tmdb(lb_watchlist, token, ttl_days)
    watched_resolved   = _resolve_lb_to_tmdb(lb_watched,   token, ttl_days)

    watchlist_ids = set(watchlist_resolved.keys())
    watched_ids   = set(watched_resolved.keys())

    # --- TMDB enrichment for currently-playing titles ---
    must_see: set = set()
    skip:     set = set()
    horror:   set = set()

    for title, year in showings:
        r = tmdb_lookup(title, year, token, ttl_days)
        if r is None:
            continue
        tid = r["tmdb_id"]

        if tid in force_skip:
            skip.add(tid); continue

        # Watched → skip (unless on watchlist — watchlist means "see again")
        if tid in watched_ids and tid not in watchlist_ids:
            skip.add(tid); continue

        # Auto-skip rules (genre / language / etc.)
        if _should_auto_skip(r, auto_rules, watchlist_ids):
            skip.add(tid); continue

        # Watchlist → must_see bonus
        if tid in watchlist_ids:
            must_see.add(tid)

        # TMDB horror genre
        if r.get("is_horror") or TMDB_HORROR_GENRE in r.get("genres", []):
            horror.add(tid)

    return TagSets(must_see=must_see, horror=horror, skip=skip)
