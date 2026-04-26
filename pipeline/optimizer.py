"""
Schedule optimizer — branch-and-bound DFS over a set of Showings.

All tag sets (must_see, horror, skip) are matched against Showing.tmdb_id when
set, falling back to Showing.title_canonical for hand-tagged overrides.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from typing import Sequence


@dataclass(frozen=True)
class Showing:
    title_raw: str
    title_canonical: str
    tmdb_id: int | None
    year: int | None
    theater_id: str
    day: date
    listed_start_min: int   # minutes from midnight
    runtime_min: int
    format: str             # IMAX / DOLBY / PRIME / 3D / STANDARD
    has_recliner: bool


@dataclass
class ScoringConfig:
    base_per_film: float    = 100.0
    must_see_bonus: float   = 50.0
    horror_bonus: float     = 30.0
    format_bonus: dict[str, float] = field(default_factory=lambda: {
        "IMAX":     5.0,
        "DOLBY":    4.0,
        "PRIME":    3.0,
        "3D":       1.0,
        "STANDARD": 0.0,
    })
    recliner_bonus: float   = 1.0
    diversity_bonus: float  = 5.0   # per distinct must-see in schedule


@dataclass
class TagSets:
    must_see: set        # tmdb_ids or canonical titles
    horror:   set        # tmdb_ids or canonical titles
    skip:     set        # tmdb_ids or canonical titles

    def _key(self, s: Showing) -> object:
        return s.tmdb_id if s.tmdb_id is not None else s.title_canonical

    def is_must_see(self, s: Showing) -> bool:
        return self._key(s) in self.must_see

    def is_horror(self, s: Showing) -> bool:
        return self._key(s) in self.horror

    def is_skip(self, s: Showing) -> bool:
        return self._key(s) in self.skip


def score_showing(s: Showing, tags: TagSets, cfg: ScoringConfig) -> float:
    v = cfg.base_per_film
    if tags.is_must_see(s):
        v += cfg.must_see_bonus
    if tags.is_horror(s):
        v += cfg.horror_bonus
    v += cfg.format_bonus.get(s.format, 0.0)
    if s.has_recliner:
        v += cfg.recliner_bonus
    return v


def solve(
    showings: Sequence[Showing],
    tags: TagSets,
    cfg: ScoringConfig | None = None,
    top_k: int = 3,
    min_diff: int = 2,
    required: set | None = None,
) -> list[list[Showing]]:
    """
    Return up to top_k diverse schedules (each pair differs by ≥ min_diff showings).
    Showings in `required` (by tmdb_id or canonical title) must appear in every
    returned schedule.

    Assumes all showings are for the same theater. Groups by day internally.
    """
    if cfg is None:
        cfg = ScoringConfig()
    required = required or set()

    candidates = [s for s in showings if not tags.is_skip(s)]
    candidates.sort(key=lambda s: (s.day, s.listed_start_min))

    scores = {id(s): score_showing(s, tags, cfg) for s in candidates}
    n = len(candidates)

    suffix_sum = [0.0] * (n + 1)
    for i in range(n - 1, -1, -1):
        suffix_sum[i] = suffix_sum[i + 1] + scores[id(candidates[i])]

    def _key(s: Showing) -> object:
        return s.tmdb_id if s.tmdb_id is not None else s.title_canonical

    def showing_id(s: Showing) -> tuple:
        return (s.title_canonical, s.day, s.listed_start_min)

    def hamming(a: list[Showing], b: list[Showing]) -> int:
        return len(set(showing_id(x) for x in a).symmetric_difference(
                   set(showing_id(x) for x in b)))

    pool: list[tuple[float, list[Showing]]] = []

    def dfs(idx: int, day_end: dict, used_keys: set,
            cur_score: float, cur_sched: list[Showing]) -> None:
        upper = cur_score + suffix_sum[idx]
        if pool and len(pool) >= top_k * 4 and upper <= pool[-1][0]:
            return

        if idx == n:
            if required and not required.issubset(used_keys):
                return
            entry = (cur_score, list(cur_sched))
            pool.append(entry)
            pool.sort(key=lambda x: -x[0])
            if len(pool) > top_k * 4:
                del pool[top_k * 4:]
            return

        s = candidates[idx]
        k = _key(s)

        # take
        if k not in used_keys and s.listed_start_min >= day_end.get(s.day, 0):
            new_end = dict(day_end)
            new_end[s.day] = s.listed_start_min + s.runtime_min - 10
            used_keys.add(k)
            cur_sched.append(s)
            dfs(idx + 1, new_end, used_keys, cur_score + scores[id(s)], cur_sched)
            cur_sched.pop()
            used_keys.remove(k)

        # skip
        dfs(idx + 1, day_end, used_keys, cur_score, cur_sched)

    dfs(0, {}, set(), 0.0, [])

    result: list[list[Showing]] = []
    for _, sched in pool:
        if len(result) >= top_k:
            break
        if all(hamming(sched, prev) >= min_diff for prev in result):
            result.append(sched)
    if not result and pool:
        result = [sched for _, sched in pool[:top_k]]
    return result


def weekend_score(schedules: list[list[Showing]], tags: TagSets,
                  cfg: ScoringConfig | None = None) -> float:
    """Total score of the best schedule (first in list = best)."""
    if cfg is None:
        cfg = ScoringConfig()
    if not schedules:
        return 0.0
    best = schedules[0]
    base = sum(score_showing(s, tags, cfg) for s in best)
    must_see_count = sum(1 for s in best if tags.is_must_see(s))
    return base + must_see_count * cfg.diversity_bonus


def tier_label(score: float, tiers: dict | None = None) -> str:
    t = tiers or {}
    if score >= t.get("marathon", 1200): return "marathon-grade weekend"
    if score >= t.get("solid",     900): return "solid day-of-movies"
    if score >= t.get("decent",    600): return "decent — a couple of films"
    return "thin weekend"
