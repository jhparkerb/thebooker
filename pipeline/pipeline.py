"""
The Booker — weekend movie schedule pipeline.

Usage:
  python -m pipeline.pipeline              # next weekend from today
  python -m pipeline.pipeline --date YYYY-MM-DD  # weekend containing that date
"""

from __future__ import annotations
import datetime
import sys
from pathlib import Path

import yaml

from pipeline.optimizer import ScoringConfig, Showing, solve, weekend_score
from pipeline.tagger import build_tag_sets
from pipeline.scrapers.amc import AMCScraper
import pipeline.digest as digest

CONFIG = Path(__file__).parent.parent / "config.yaml"


def _load_cfg() -> dict:
    return yaml.safe_load(CONFIG.read_text())


def _scoring_cfg(cfg: dict) -> ScoringConfig:
    s = cfg.get("scoring", {})
    defaults = ScoringConfig()
    return ScoringConfig(
        base_per_film   = s.get("base_per_film",   defaults.base_per_film),
        must_see_bonus  = s.get("must_see_bonus",  defaults.must_see_bonus),
        horror_bonus    = s.get("horror_bonus",    defaults.horror_bonus),
        format_bonus    = s.get("format_bonus",    defaults.format_bonus),
        recliner_bonus  = s.get("recliner_bonus",  defaults.recliner_bonus),
        diversity_bonus = s.get("diversity_bonus", defaults.diversity_bonus),
    )


def _weekend_days(anchor: datetime.date) -> list[datetime.date]:
    """Return [Saturday, Sunday] on or after anchor."""
    days_ahead = (5 - anchor.weekday()) % 7
    sat = anchor + datetime.timedelta(days=days_ahead)
    return [sat, sat + datetime.timedelta(days=1)]


def _make_scraper(theater_cfg: dict):
    chain = theater_cfg["chain"]
    if chain == "amc":
        return AMCScraper(theater_cfg["chain_id"], theater_cfg["name"])
    raise ValueError(f"unsupported chain: {chain!r}")


def run(cfg: dict, days: list[datetime.date]) -> None:
    scoring = _scoring_cfg(cfg)

    # Fetch showings per theater
    theater_showings: dict[str, list[Showing]] = {}
    for t in cfg["theaters"]:
        showings: list[Showing] = []
        try:
            scraper = _make_scraper(t)
        except ValueError as e:
            print(f"[pipeline] skipping {t['name']}: {e}", file=sys.stderr)
            continue
        for day in days:
            try:
                showings.extend(scraper.fetch(t["chain_id"], day))
            except Exception as e:
                print(f"[pipeline] {t['name']} {day}: {e}", file=sys.stderr)
        theater_showings[t["id"]] = showings

    # Build tag sets once, across all titles currently playing
    all_titles = list({(s.title_raw, s.year)
                       for showings in theater_showings.values()
                       for s in showings})
    tags = build_tag_sets(cfg, all_titles)

    # Optimize per theater, collect (theater_cfg, best_schedule, score)
    results: list[tuple[dict, list[Showing], float]] = []
    for t in cfg["theaters"]:
        showings = theater_showings.get(t["id"], [])
        if not showings:
            continue
        schedules = solve(showings, tags, scoring)
        score     = weekend_score(schedules, tags, scoring)
        results.append((t, schedules[0] if schedules else [], score))

    results.sort(key=lambda x: x[2], reverse=True)
    digest.render(results, tags, days, cfg)


def main() -> None:
    cfg    = _load_cfg()
    anchor = datetime.date.today()
    if "--date" in sys.argv:
        idx    = sys.argv.index("--date")
        anchor = datetime.date.fromisoformat(sys.argv[idx + 1])
    run(cfg, _weekend_days(anchor))


if __name__ == "__main__":
    main()
