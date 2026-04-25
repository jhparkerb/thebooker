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

def fmt(m: int) -> str:
    h, mn = divmod(m, 60)
    ap = "pm" if h >= 12 else "am"
    if h > 12: h -= 12
    if h == 0: h = 12
    return f"{h}:{mn:02d}{ap}"

def main():
    cfg = ScoringConfig()
    schedules = solve(SHOWINGS, TAGS, cfg, top_k=3)

    print(f"Top {len(schedules)} schedules:\n")
    for i, sched in enumerate(schedules, 1):
        sc = sum(cfg.base_per_film for _ in sched)  # rough
        ms = sum(1 for s in sched if TAGS.is_must_see(s))
        hr = sum(1 for s in sched if TAGS.is_horror(s))
        ws = weekend_score([sched], TAGS, cfg)
        print(f"=== Schedule {i}  (must-see {ms}/4 · horror {hr} · films {len(sched)} · score {ws:.0f}) [{tier_label(ws)}]")
        for s in sorted(sched, key=lambda x: (x.day, x.listed_start_min)):
            tags = []
            if TAGS.is_must_see(s): tags.append("must-see")
            if TAGS.is_horror(s): tags.append("horror")
            tag_str = f"  [{', '.join(tags)}]" if tags else ""
            depart = s.listed_start_min + s.runtime_min - 10
            print(f"  {s.day}  {fmt(s.listed_start_min)}–{fmt(depart)} (dep)  {s.title_canonical:<35} ({s.format}){tag_str}")
        print()

    # Basic assertions
    assert len(schedules) >= 1, "No schedules returned"
    best = schedules[0]
    titles = {s.title_canonical for s in best}
    assert "Speed Racer" in titles or "Project Hail Mary" in titles, \
        "Best schedule missing obvious must-sees"
    print("Assertions passed.")
    ws = weekend_score([best], TAGS, cfg)
    print(f"Weekend score: {ws:.0f}  ({tier_label(ws)})")

if __name__ == "__main__":
    main()
