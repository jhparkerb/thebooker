"""
Formats the ranked weekend digest to stdout.
Maintains cache/last_digest.json for new-since-last-run diffing.
"""

from __future__ import annotations
import json
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

from pipeline.optimizer import Showing, TagSets, tier_label

CACHE_PATH = Path(__file__).parent / "cache" / "last_digest.json"

ATTRIBUTION = (
    "This application uses TMDB and the TMDB APIs but is not endorsed, "
    "certified, or otherwise approved by TMDB."
)


def _fmt_time(minutes: int) -> str:
    h, m = divmod(minutes, 60)
    ap = "pm" if h >= 12 else "am"
    return f"{h % 12 or 12}:{m:02d}{ap}"


def _showing_tags(s: Showing, tags: TagSets) -> str:
    parts = []
    if tags.is_must_see(s):        parts.append("must-see")
    if tags.is_horror(s):          parts.append("horror")
    if s.format != "STANDARD":     parts.append(s.format)
    if s.has_recliner:             parts.append("recliner")
    return f"[{', '.join(parts)}]" if parts else ""


def _day_summary(showings: list[Showing], tags: TagSets) -> str:
    n  = len(showings)
    ms = sum(1 for s in showings if tags.is_must_see(s))
    hr = sum(1 for s in showings if tags.is_horror(s))
    parts = [f"{n} film{'s' if n != 1 else ''}"]
    if ms: parts.append(f"{ms} must-see")
    if hr: parts.append(f"{hr} horror")
    return " · ".join(parts)


def render(
    results: list[tuple[dict, list[Showing], float]],
    tags: TagSets,
    days: list[date],
    cfg: dict,
) -> None:
    tiers = cfg.get("tiers", {})

    if len(days) >= 2:
        span = f"{days[0].strftime('%b %-d')}–{days[-1].strftime('%-d, %Y')}"
    else:
        span = days[0].strftime("%b %-d, %Y")
    print(f"=== WEEKEND DIGEST · {span} ===")
    print(f"generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    if not results:
        print("No showings found.")
        print()
        print(ATTRIBUTION)
        return

    top_score = results[0][2]
    print(f"Top score: {top_score:.0f}  ({tier_label(top_score, tiers)})")
    print()

    for rank, (theater_cfg, schedule, score) in enumerate(results, 1):
        print(f"#{rank}  {theater_cfg['name']:<46} score {score:>5.0f}  [{tier_label(score, tiers)}]")

        if not schedule:
            print("    (no viable schedule)")
            print()
            continue

        by_day: defaultdict[date, list[Showing]] = defaultdict(list)
        for s in schedule:
            by_day[s.day].append(s)

        for day in days:
            day_showings = sorted(by_day.get(day, []), key=lambda s: s.listed_start_min)
            if not day_showings:
                continue
            print(f"    {day.strftime('%a %b %-d')}  ({_day_summary(day_showings, tags)})")
            for s in day_showings:
                end_min  = s.listed_start_min + s.runtime_min
                timespan = f"{_fmt_time(s.listed_start_min)}–{_fmt_time(end_min)}"
                title    = s.title_canonical or s.title_raw
                tag_str  = _showing_tags(s, tags)
                print(f"      {timespan:<17}  {title:<38}  {tag_str}")
        print()

    # Dropped must-sees: in tags.must_see but not in any theater's best schedule
    scheduled_keys: set = set()
    for _, schedule, _ in results:
        for s in schedule:
            scheduled_keys.add(s.tmdb_id if s.tmdb_id is not None else s.title_canonical)

    dropped = [k for k in tags.must_see if k not in scheduled_keys]
    if dropped:
        print("DROPPED MUST-SEES (not in any theater's best schedule):")
        for k in dropped:
            print(f"  - {k}")
        print()

    _diff_and_save(results, days)

    print(ATTRIBUTION)


def _diff_and_save(
    results: list[tuple[dict, list[Showing], float]],
    days: list[date],
) -> None:
    prev: dict[str, list[str]] = {}
    if CACHE_PATH.exists():
        try:
            prev = json.loads(CACHE_PATH.read_text()).get("schedules", {})
        except (json.JSONDecodeError, KeyError):
            pass

    current: dict[str, list[str]] = {}
    new_items: list[str] = []
    for theater_cfg, sched, _ in results:
        tid    = theater_cfg["id"]
        name   = theater_cfg["name"]
        titles = sorted({s.title_canonical or s.title_raw for s in sched})
        current[tid] = titles
        prev_titles = set(prev.get(tid, []))
        for title in titles:
            if title not in prev_titles:
                new_items.append(f"  - {title!r} at {name}")

    if new_items:
        print("NEW SINCE LAST DIGEST:")
        for item in new_items:
            print(item)
        print()

    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps({
        "generated": datetime.now().isoformat(),
        "days":      [d.isoformat() for d in days],
        "schedules": current,
    }, indent=2))
