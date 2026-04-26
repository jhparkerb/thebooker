"""
Formats the ranked weekend digest to stdout.
Maintains cache/last_digest.json for new-since-last-run diffing.
"""

from __future__ import annotations
from collections import defaultdict
from datetime import date, datetime

from pipeline.optimizer import Showing, TagSets, tier_label

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


def _end_min(s: Showing, is_last: bool) -> tuple[int, bool]:
    """Return (end_minutes, is_depart). Non-final films depart 10 min early (credits)."""
    if is_last:
        return s.listed_start_min + s.runtime_min, False
    return s.listed_start_min + s.runtime_min - 10, True


def _schedule_header(schedule: list[Showing], tags: TagSets,
                     sched_score: float, must_see_total: int) -> str:
    ms = sum(1 for s in schedule if tags.is_must_see(s))
    hr = sum(1 for s in schedule if tags.is_horror(s))
    return (f"must-see {ms}/{must_see_total} · horror {hr} · "
            f"films {len(schedule)} · score {sched_score:.0f}")


def _dropped_must_sees(schedules: list[list[Showing]], tags: TagSets) -> set:
    seen: set = set()
    for sched in schedules:
        for s in sched:
            if tags.is_must_see(s):
                seen.add(tags._key(s))
    return tags.must_see - seen


def _render_schedule(schedule: list[Showing], tags: TagSets, days: list[date],
                     indent: str = "    ") -> None:
    by_day: defaultdict[date, list[Showing]] = defaultdict(list)
    for s in schedule:
        by_day[s.day].append(s)
    for day in days:
        day_showings = sorted(by_day.get(day, []), key=lambda s: s.listed_start_min)
        if not day_showings:
            continue
        print(f"{indent}{day.strftime('%a %b %-d')}  ({_day_summary(day_showings, tags)})")
        for idx, s in enumerate(day_showings):
            end_min, is_depart = _end_min(s, idx == len(day_showings) - 1)
            depart_note = " (depart)" if is_depart else ""
            timespan = f"{_fmt_time(s.listed_start_min)}–{_fmt_time(end_min)}{depart_note}"
            title    = s.title_canonical or s.title_raw
            print(f"{indent}  {timespan:<26}  {title:<38}  {_showing_tags(s, tags)}")


def render(
    results: list[tuple[dict, list[tuple[list[Showing], float]], float]],
    tags: TagSets,
    days: list[date],
    cfg: dict,
) -> None:
    tiers = cfg.get("tiers", {})
    must_see_total = len(tags.must_see)

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

    for rank, (theater_cfg, scored_schedules, score) in enumerate(results, 1):
        print(f"#{rank}  {theater_cfg['name']:<46} score {score:>5.0f}  [{tier_label(score, tiers)}]")

        if not scored_schedules:
            print("    (no viable schedule)")
            print()
            continue

        for i, (schedule, sched_score) in enumerate(scored_schedules):
            label = "primary" if i == 0 else f"alt {i}"
            header = _schedule_header(schedule, tags, sched_score, must_see_total)
            print(f"    --- {label}: {header} ---")
            _render_schedule(schedule, tags, days)

        all_schedules = [s for s, _ in scored_schedules]
        dropped = _dropped_must_sees(all_schedules, tags)
        if dropped:
            print(f"    !! DROPPED MUST-SEES: {', '.join(str(k) for k in sorted(dropped, key=str))}")
        else:
            print("    All must-sees appear in at least one schedule.")
        print()

    print(ATTRIBUTION)
