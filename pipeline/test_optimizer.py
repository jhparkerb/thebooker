"""
Regression test: optimizer.py on the Apr 25-26 2026 weekend.
Expected top schedule: Saturday horror marathon + Sunday must-see day,
matching what schedule.py produced.
Run: python -m pipeline.test_optimizer
"""

import sys
from datetime import date
from pipeline.optimizer import Showing, TagSets, ScoringConfig, solve, weekend_score, tier_label

SAT = date(2026, 4, 25)
SUN = date(2026, 4, 26)
T = "amc-waterfront-22"

def t(s: str) -> int:
    h, rest = s.split(":")
    m = int(rest[:2])
    pm = rest.endswith("p") and h != "12"
    return int(h) * 60 + m + (720 if pm else 0)

SHOWINGS = [
    Showing("Exit 8 (2025)",            "Exit 8",                   None, 2025, T, SAT, t("5:10p"), 95,  "STANDARD", False),
    Showing("Exit 8 (2025)",            "Exit 8",                   None, 2025, T, SUN, t("5:00p"), 95,  "STANDARD", False),
    Showing("Exit 8 (2025)",            "Exit 8",                   None, 2025, T, SUN, t("10:30p"),95,  "STANDARD", False),
    Showing("The Silence of the Lambs 35th Anniversary", "The Silence of the Lambs", None, 1991, T, SUN, t("4:00p"), 123, "STANDARD", False),
    Showing("Fuze (2026)",              "Fuze",                     None, 2026, T, SAT, t("1:35p"), 97,  "STANDARD", False),
    Showing("Fuze (2026)",              "Fuze",                     None, 2026, T, SAT, t("4:15p"), 97,  "STANDARD", False),
    Showing("Fuze (2026)",              "Fuze",                     None, 2026, T, SAT, t("7:00p"), 97,  "STANDARD", False),
    Showing("Fuze (2026)",              "Fuze",                     None, 2026, T, SAT, t("10:10p"),97,  "STANDARD", True),
    Showing("Fuze (2026)",              "Fuze",                     None, 2026, T, SUN, t("1:35p"), 97,  "STANDARD", False),
    Showing("Fuze (2026)",              "Fuze",                     None, 2026, T, SUN, t("4:15p"), 97,  "STANDARD", False),
    Showing("Fuze (2026)",              "Fuze",                     None, 2026, T, SUN, t("7:00p"), 97,  "STANDARD", False),
    Showing("Fuze (2026)",              "Fuze",                     None, 2026, T, SUN, t("10:15p"),97,  "STANDARD", True),
    Showing("Over Your Dead Body (2026)","Over Your Dead Body",     None, 2026, T, SAT, t("7:30p"), 105, "STANDARD", True),
    Showing("Over Your Dead Body (2026)","Over Your Dead Body",     None, 2026, T, SUN, t("7:30p"), 105, "STANDARD", True),
    Showing("Fight Club 4K Remaster",   "Fight Club",               None, 1999, T, SAT, t("1:55p"), 139, "STANDARD", False),
    Showing("Fight Club 4K Remaster",   "Fight Club",               None, 1999, T, SAT, t("10:15p"),139, "STANDARD", False),
    Showing("Fight Club 4K Remaster",   "Fight Club",               None, 1999, T, SUN, t("2:00p"), 139, "STANDARD", False),
    Showing("Fight Club 4K Remaster",   "Fight Club",               None, 1999, T, SUN, t("7:00p"), 139, "STANDARD", False),
    Showing("Fight Club 4K Remaster",   "Fight Club",               None, 1999, T, SUN, t("10:15p"),139, "STANDARD", False),
    Showing("Speed Racer (2026)",       "Speed Racer",              None, 2026, T, SAT, t("4:15p"), 120, "STANDARD", True),
    Showing("Speed Racer (2026)",       "Speed Racer",              None, 2026, T, SAT, t("10:15p"),120, "STANDARD", False),
    Showing("Speed Racer (2026)",       "Speed Racer",              None, 2026, T, SUN, t("1:45p"), 120, "STANDARD", False),
    Showing("Speed Racer (2026)",       "Speed Racer",              None, 2026, T, SUN, t("4:15p"), 120, "STANDARD", True),
    Showing("Speed Racer (2026)",       "Speed Racer",              None, 2026, T, SUN, t("10:30a"),120, "STANDARD", True),
    Showing("Lee Cronin's The Mummy (2026)","Lee Cronin's The Mummy",None,2026, T, SAT, t("12:15p"),133, "STANDARD", True),
    Showing("Lee Cronin's The Mummy (2026)","Lee Cronin's The Mummy",None,2026, T, SAT, t("3:30p"), 133, "STANDARD", True),
    Showing("Lee Cronin's The Mummy (2026)","Lee Cronin's The Mummy",None,2026, T, SUN, t("12:15p"),133, "STANDARD", True),
    Showing("Mother Mary (2026)",       "Mother Mary",              None, 2026, T, SAT, t("12:55p"),112, "STANDARD", True),
    Showing("Mother Mary (2026)",       "Mother Mary",              None, 2026, T, SAT, t("3:45p"), 112, "STANDARD", True),
    Showing("Mother Mary (2026)",       "Mother Mary",              None, 2026, T, SAT, t("6:35p"), 112, "STANDARD", True),
    Showing("Mother Mary (2026)",       "Mother Mary",              None, 2026, T, SAT, t("9:25p"), 112, "STANDARD", True),
    Showing("Mother Mary (2026)",       "Mother Mary",              None, 2026, T, SUN, t("12:55p"),112, "STANDARD", True),
    Showing("Normal (2026)",            "Normal",                   None, 2026, T, SAT, t("1:15p"), 91,  "STANDARD", True),
    Showing("Normal (2026)",            "Normal",                   None, 2026, T, SAT, t("2:40p"), 91,  "STANDARD", True),
    Showing("The Christophers (2026)",  "The Christophers",         None, 2026, T, SAT, t("8:20p"), 100, "STANDARD", True),
    Showing("The Christophers (2026)",  "The Christophers",         None, 2026, T, SUN, t("1:00p"), 100, "STANDARD", True),
    Showing("Project Hail Mary (2026)", "Project Hail Mary",        None, 2026, T, SAT, t("9:50p"), 156, "PRIME",    True),
    Showing("Project Hail Mary (2026)", "Project Hail Mary",        None, 2026, T, SUN, t("12:30p"),156, "PRIME",    True),
    Showing("Project Hail Mary (2026)", "Project Hail Mary",        None, 2026, T, SUN, t("3:45p"), 156, "PRIME",    True),
    Showing("Project Hail Mary (2026)", "Project Hail Mary",        None, 2026, T, SUN, t("9:50p"), 156, "PRIME",    True),
    Showing("Hoppers (2026)",           "Hoppers",                  None, 2026, T, SAT, t("1:15p"), 95,  "STANDARD", False),
    Showing("Hoppers (2026)",           "Hoppers",                  None, 2026, T, SAT, t("4:00p"), 95,  "3D",       False),
    Showing("Hoppers (2026)",           "Hoppers",                  None, 2026, T, SUN, t("1:15p"), 95,  "STANDARD", False),
    Showing("Broken Bird (2026)",       "Broken Bird",              None, 2026, T, SAT, t("1:30p"), 99,  "STANDARD", True),
    Showing("Broken Bird (2026)",       "Broken Bird",              None, 2026, T, SUN, t("1:30p"), 99,  "STANDARD", True),
]

TAGS = TagSets(
    must_see={"The Silence of the Lambs", "Speed Racer", "Project Hail Mary", "Hoppers"},
    horror={"Lee Cronin's The Mummy", "Mother Mary", "Over Your Dead Body", "Exit 8"},
    skip=set(),
)


# --- pytest functions ---

def test_solve_returns_schedules():
    assert len(solve(SHOWINGS, TAGS, ScoringConfig(), top_k=3)) >= 1

def test_solve_best_has_must_sees():
    best = solve(SHOWINGS, TAGS, ScoringConfig())[0]
    titles = {s.title_canonical for s in best}
    assert titles & {"Speed Racer", "Project Hail Mary", "Hoppers", "The Silence of the Lambs"}, \
        f"best schedule has no must-sees: {titles}"

def test_solve_skips_are_excluded():
    tags = TagSets(must_see=set(), horror=set(), skip={"Exit 8"})
    for sched in solve(SHOWINGS, tags, ScoringConfig()):
        assert not any(s.title_canonical == "Exit 8" for s in sched)

def test_solve_default_cfg():
    schedules = solve(SHOWINGS, TAGS)
    assert schedules

def test_solve_top_k_diversity():
    schedules = solve(SHOWINGS, TAGS, ScoringConfig(), top_k=3)
    def key(s): return (s.title_canonical, s.day, s.listed_start_min)
    def hamming(a, b): return len({key(x) for x in a}.symmetric_difference({key(x) for x in b}))
    for i, a in enumerate(schedules):
        for b in schedules[i+1:]:
            assert hamming(a, b) >= 2

def test_weekend_score_empty():
    assert weekend_score([], TAGS) == 0.0

def test_weekend_score_default_cfg():
    schedules = solve(SHOWINGS, TAGS, ScoringConfig())
    assert weekend_score(schedules, TAGS) > 0

def test_weekend_score_marathon():
    schedules = solve(SHOWINGS, TAGS, ScoringConfig())
    assert weekend_score(schedules, TAGS) >= 1200

def test_tier_label_all_tiers():
    assert tier_label(1200) == "marathon-grade weekend"
    assert tier_label(900)  == "solid day-of-movies"
    assert tier_label(600)  == "decent — a couple of films"
    assert tier_label(599)  == "thin weekend"

def test_tier_label_custom_thresholds():
    tiers = {"marathon": 500, "solid": 300, "decent": 100}
    assert tier_label(600, tiers) == "marathon-grade weekend"
    assert tier_label(400, tiers) == "solid day-of-movies"
    assert tier_label(200, tiers) == "decent — a couple of films"
    assert tier_label(50,  tiers) == "thin weekend"


# --- required param ---

def test_solve_required_appears_in_all_schedules():
    schedules = solve(SHOWINGS, TAGS, ScoringConfig(), required={"Project Hail Mary"})
    assert schedules, "expected at least one schedule"
    for sched in schedules:
        assert any(s.title_canonical == "Project Hail Mary" for s in sched)

def test_solve_required_empty_set_unchanged():
    without = solve(SHOWINGS, TAGS, ScoringConfig())
    with_empty = solve(SHOWINGS, TAGS, ScoringConfig(), required=set())
    assert len(with_empty) == len(without)

def test_solve_required_impossible_returns_empty():
    assert solve(SHOWINGS, TAGS, ScoringConfig(), required={"Nonexistent Film"}) == []

def test_solve_required_none_is_default():
    assert solve(SHOWINGS, TAGS, ScoringConfig(), required=None) == \
           solve(SHOWINGS, TAGS, ScoringConfig())


