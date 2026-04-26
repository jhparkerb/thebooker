"""
Parity check: pipeline solve() vs legacy schedule.py on the Apr 25-26 fixture.
This file is deleted together with schedule.py once parity is confirmed.
"""

from datetime import date
import schedule as legacy
from pipeline.optimizer import Showing, TagSets, ScoringConfig, solve

T = "amc-waterfront-22"
SAT = date(2026, 4, 25)
SUN = date(2026, 4, 26)

def _day(d: int) -> date:
    return SAT if d == 0 else SUN

PIPELINE_SHOWINGS = [
    Showing(title_raw=s[0], title_canonical=s[0], tmdb_id=None, year=None,
            theater_id=T, day=_day(s[1]),
            listed_start_min=s[2], runtime_min=s[3],
            format=s[4], has_recliner=s[5])
    for s in legacy.SHOWINGS
]

PIPELINE_TAGS = TagSets(
    must_see=set(legacy.MUST_SEE),
    horror=set(legacy.HORROR),
    skip=set(legacy.SKIP),
)


def test_pipeline_returns_schedules():
    assert solve(PIPELINE_SHOWINGS, PIPELINE_TAGS, ScoringConfig())


def test_pipeline_best_schedule_has_same_must_sees_as_legacy():
    legacy_scheds = legacy.solve(legacy.SHOWINGS)
    pipeline_scheds = solve(PIPELINE_SHOWINGS, PIPELINE_TAGS, ScoringConfig())

    legacy_best_ms = {c[0] for c in legacy_scheds[0] if c[0] in legacy.MUST_SEE}
    pipeline_best_ms = {s.title_canonical for s in pipeline_scheds[0]
                        if s.title_canonical in legacy.MUST_SEE}
    assert pipeline_best_ms == legacy_best_ms, (
        f"must-see mismatch: pipeline={pipeline_best_ms} legacy={legacy_best_ms}"
    )


def test_pipeline_schedule_count_matches():
    legacy_scheds = legacy.solve(legacy.SHOWINGS, top_k=3)
    pipeline_scheds = solve(PIPELINE_SHOWINGS, PIPELINE_TAGS, ScoringConfig(), top_k=3)
    assert len(pipeline_scheds) == len(legacy_scheds)
