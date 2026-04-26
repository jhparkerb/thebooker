"""
The Booker — weekend movie schedule pipeline.

Usage:
  python -m pipeline.pipeline              # next weekend from today
  python -m pipeline.pipeline --date YYYY-MM-DD  # weekend containing that date
"""

from __future__ import annotations
import argparse
import dataclasses
import datetime
from pathlib import Path

import yaml

import sys

from pipeline.optimizer import ScoringConfig, Showing, solve, weekend_score
from pipeline.tagger import build_tag_sets
from pipeline.scrapers.amc import AMCScraper
import pipeline.digest as digest

CONFIG = Path(__file__).parent.parent / "config.yaml"


def _load_cfg() -> dict:
    return yaml.safe_load(CONFIG.read_text())


def _scoring_cfg(cfg: dict) -> ScoringConfig:
    s = cfg.get("scoring", {})
    valid = {f.name for f in dataclasses.fields(ScoringConfig)}
    return ScoringConfig(**{k: v for k, v in s.items() if k in valid})


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

    all_titles = list({(s.title_raw, s.year)
                       for showings in theater_showings.values()
                       for s in showings})
    tags = build_tag_sets(cfg, all_titles)

    results: list[tuple[dict, list[tuple[list[Showing], float]], float]] = []
    for t in cfg["theaters"]:
        showings = theater_showings.get(t["id"], [])
        if not showings:
            continue
        schedules  = solve(showings, tags, scoring)
        top_score  = weekend_score(schedules, tags, scoring)
        scored     = [(s, weekend_score([s], tags, scoring)) for s in schedules]
        results.append((t, scored, top_score))

    results.sort(key=lambda x: x[2], reverse=True)
    digest.render(results, tags, days, cfg)


def main() -> None:
    parser = argparse.ArgumentParser(description="The Booker — weekend movie digest")
    parser.add_argument("--date", metavar="YYYY-MM-DD",
                        type=datetime.date.fromisoformat,
                        default=datetime.date.today(),
                        help="anchor date (defaults to today)")
    args = parser.parse_args()
    run(_load_cfg(), _weekend_days(args.date))


if __name__ == "__main__":
    main()
