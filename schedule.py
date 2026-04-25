"""
AMC Waterfront 22 — two-day schedule optimizer
Days: Fri Apr 25 (day=0) and Sat Apr 26 (day=1)
Times are minutes from midnight.
"""

def t(time_str):
    """Convert '1:40p', '12:00p', '10:25p', etc. to minutes from midnight."""
    time_str = time_str.strip()
    pm = time_str.endswith('p')
    time_str = time_str[:-1]
    h, m = map(int, time_str.split(':'))
    if pm and h != 12:
        h += 12
    elif not pm and h == 12:
        h = 0
    return h * 60 + m

# ---------------------------------------------------------------------------
# SHOWINGS: (title, day, listed_start_min, runtime_min, format, has_recliner)
# day 0 = Fri Apr 25, day 1 = Sat Apr 26
# format: IMAX > PRIME > 3D > STANDARD
# ---------------------------------------------------------------------------
SHOWINGS = [
    # --- Exit 8 (2025) PG-13 1h35 ---
    ("Exit 8 (2025)",            0, t("5:10p"), 95,  "STANDARD", False),
    ("Exit 8 (2025)",            1, t("5:00p"), 95,  "STANDARD", False),
    ("Exit 8 (2025)",            1, t("10:30p"),95,  "STANDARD", False),

    # --- The Silence of the Lambs 35th Anniversary  R 2h03 --- Apr 26 only
    ("The Silence of the Lambs 35th Anniversary", 1, t("4:00p"), 123, "STANDARD", False),

    # --- Desert Warrior (2026)  R 1h54 ---
    ("Desert Warrior (2026)",    0, t("1:40p"), 114, "STANDARD", True),
    ("Desert Warrior (2026)",    0, t("4:35p"), 114, "STANDARD", True),
    ("Desert Warrior (2026)",    0, t("7:30p"), 114, "STANDARD", True),
    ("Desert Warrior (2026)",    0, t("10:25p"),114, "STANDARD", True),
    ("Desert Warrior (2026)",    1, t("1:40p"), 114, "STANDARD", True),
    ("Desert Warrior (2026)",    1, t("4:35p"), 114, "STANDARD", True),
    ("Desert Warrior (2026)",    1, t("7:30p"), 114, "STANDARD", True),
    ("Desert Warrior (2026)",    1, t("10:25p"),114, "STANDARD", False),

    # --- Fuze (2026)  R 1h37 ---
    ("Fuze (2026)",              0, t("1:35p"), 97,  "STANDARD", False),
    ("Fuze (2026)",              0, t("4:15p"), 97,  "STANDARD", False),
    ("Fuze (2026)",              0, t("7:00p"), 97,  "STANDARD", False),
    ("Fuze (2026)",              0, t("10:10p"),97,  "STANDARD", True),
    ("Fuze (2026)",              1, t("1:35p"), 97,  "STANDARD", False),
    ("Fuze (2026)",              1, t("4:15p"), 97,  "STANDARD", False),
    ("Fuze (2026)",              1, t("7:00p"), 97,  "STANDARD", False),
    ("Fuze (2026)",              1, t("10:15p"),97,  "STANDARD", True),

    # --- Michael (2026)  PG-13 2h07 --- (SKIP — in SKIP list)
    # omitted

    # --- Over Your Dead Body (2026)  R 1h45 ---
    ("Over Your Dead Body (2026)", 0, t("7:30p"), 105, "STANDARD", True),
    ("Over Your Dead Body (2026)", 1, t("7:30p"), 105, "STANDARD", True),

    # --- Fight Club 4K Remaster (2026)  R 2h19 ---
    ("Fight Club 4K Remaster (2026)", 0, t("1:55p"), 139, "STANDARD", False),
    ("Fight Club 4K Remaster (2026)", 0, t("10:15p"),139, "STANDARD", False),
    ("Fight Club 4K Remaster (2026)", 1, t("2:00p"), 139, "STANDARD", False),
    ("Fight Club 4K Remaster (2026)", 1, t("7:00p"), 139, "STANDARD", False),
    ("Fight Club 4K Remaster (2026)", 1, t("10:15p"),139, "STANDARD", False),

    # --- Whisper of the Heart 4K (2026)  G 1h51 ---
    ("Whisper of the Heart 4K (2026)", 0, t("7:25p"), 111, "STANDARD", True),
    ("Whisper of the Heart 4K (2026)", 0, t("10:20p"),111, "STANDARD", True),
    ("Whisper of the Heart 4K (2026)", 1, t("7:25p"), 111, "STANDARD", True),
    ("Whisper of the Heart 4K (2026)", 1, t("10:20p"),111, "STANDARD", True),

    # --- Speed Racer (2026)  PG 2h10 ---
    ("Speed Racer (2026)",       0, t("1:55p"), 130, "STANDARD", False),
    ("Speed Racer (2026)",       0, t("4:15p"), 130, "STANDARD", True),
    ("Speed Racer (2026)",       0, t("10:15p"),130, "STANDARD", False),
    ("Speed Racer (2026)",       1, t("1:45p"), 130, "STANDARD", False),
    ("Speed Racer (2026)",       1, t("4:15p"), 130, "STANDARD", True),
    ("Speed Racer (2026)",       1, t("10:10p"),130, "STANDARD", False),

    # --- Lee Cronin's The Mummy (2026)  R 2h13 ---
    ("Lee Cronin's The Mummy (2026)", 0, t("12:15p"),133, "STANDARD", True),
    ("Lee Cronin's The Mummy (2026)", 0, t("3:30p"), 133, "STANDARD", True),
    ("Lee Cronin's The Mummy (2026)", 0, t("6:45p"), 133, "STANDARD", True),
    ("Lee Cronin's The Mummy (2026)", 0, t("10:00p"),133, "STANDARD", True),
    ("Lee Cronin's The Mummy (2026)", 1, t("12:15p"),133, "STANDARD", True),
    ("Lee Cronin's The Mummy (2026)", 1, t("3:30p"), 133, "STANDARD", True),
    ("Lee Cronin's The Mummy (2026)", 1, t("6:45p"), 133, "STANDARD", True),
    ("Lee Cronin's The Mummy (2026)", 1, t("10:00p"),133, "STANDARD", True),

    # --- Lorne (2026)  R 1h41 --- (SKIP)
    # omitted

    # --- Mother Mary (2026)  R 1h52 ---
    ("Mother Mary (2026)",       0, t("12:55p"),112, "STANDARD", True),
    ("Mother Mary (2026)",       0, t("3:45p"), 112, "STANDARD", True),
    ("Mother Mary (2026)",       0, t("6:35p"), 112, "STANDARD", True),
    ("Mother Mary (2026)",       0, t("9:25p"), 112, "STANDARD", True),
    ("Mother Mary (2026)",       1, t("12:55p"),112, "STANDARD", True),
    ("Mother Mary (2026)",       1, t("3:45p"), 112, "STANDARD", True),
    ("Mother Mary (2026)",       1, t("6:35p"), 112, "STANDARD", True),
    ("Mother Mary (2026)",       1, t("9:25p"), 112, "STANDARD", True),

    # --- Normal (2026)  R 1h31 ---
    ("Normal (2026)",            0, t("1:15p"), 91,  "STANDARD", True),
    ("Normal (2026)",            0, t("2:40p"), 91,  "STANDARD", True),
    ("Normal (2026)",            0, t("10:20p"),91,  "STANDARD", False),
    ("Normal (2026)",            1, t("1:15p"), 91,  "STANDARD", True),
    ("Normal (2026)",            1, t("5:25p"), 91,  "STANDARD", True),
    ("Normal (2026)",            1, t("8:00p"), 91,  "STANDARD", True),
    ("Normal (2026)",            1, t("10:30p"),91,  "STANDARD", True),

    # --- The Christophers (2026)  R 1h40 ---
    ("The Christophers (2026)",  0, t("12:45p"),100, "STANDARD", False),
    ("The Christophers (2026)",  0, t("8:20p"), 100, "STANDARD", True),
    ("The Christophers (2026)",  1, t("12:45p"),100, "STANDARD", False),
    ("The Christophers (2026)",  1, t("2:45p"), 100, "STANDARD", True),

    # --- You, Me & Tuscany (2026)  PG-13 1h44 ---
    ("You, Me & Tuscany (2026)", 0, t("1:40p"), 104, "STANDARD", True),
    ("You, Me & Tuscany (2026)", 0, t("4:25p"), 104, "STANDARD", True),
    ("You, Me & Tuscany (2026)", 0, t("7:10p"), 104, "STANDARD", True),
    ("You, Me & Tuscany (2026)", 0, t("9:55p"), 104, "STANDARD", True),
    ("You, Me & Tuscany (2026)", 1, t("1:40p"), 104, "STANDARD", True),
    ("You, Me & Tuscany (2026)", 1, t("4:25p"), 104, "STANDARD", True),
    ("You, Me & Tuscany (2026)", 1, t("7:10p"), 104, "STANDARD", True),
    ("You, Me & Tuscany (2026)", 1, t("9:55p"), 104, "STANDARD", True),

    # --- The Drama (2026)  R 1h46 ---
    ("The Drama (2026)",         0, t("1:45p"), 106, "STANDARD", True),
    ("The Drama (2026)",         0, t("4:35p"), 106, "STANDARD", True),
    ("The Drama (2026)",         0, t("7:25p"), 106, "STANDARD", True),
    ("The Drama (2026)",         0, t("10:15p"),106, "STANDARD", True),
    ("The Drama (2026)",         1, t("1:45p"), 106, "STANDARD", True),
    ("The Drama (2026)",         1, t("4:35p"), 106, "STANDARD", True),
    ("The Drama (2026)",         1, t("7:25p"), 106, "STANDARD", True),
    ("The Drama (2026)",         1, t("10:15p"),106, "STANDARD", True),

    # --- Project Hail Mary (2026)  PG-13 2h36 ---
    ("Project Hail Mary (2026)", 0, t("2:40p"), 156, "PRIME",    True),
    ("Project Hail Mary (2026)", 0, t("6:15p"), 156, "PRIME",    True),
    ("Project Hail Mary (2026)", 0, t("9:50p"), 156, "PRIME",    True),
    ("Project Hail Mary (2026)", 0, t("12:35p"),156, "STANDARD", True),
    ("Project Hail Mary (2026)", 0, t("3:50p"), 156, "STANDARD", True),
    ("Project Hail Mary (2026)", 0, t("8:55p"), 156, "STANDARD", True),
    ("Project Hail Mary (2026)", 1, t("2:40p"), 156, "PRIME",    True),
    ("Project Hail Mary (2026)", 1, t("6:15p"), 156, "PRIME",    True),
    ("Project Hail Mary (2026)", 1, t("9:50p"), 156, "PRIME",    True),
    ("Project Hail Mary (2026)", 1, t("12:35p"),156, "STANDARD", True),
    ("Project Hail Mary (2026)", 1, t("3:50p"), 156, "STANDARD", True),
    ("Project Hail Mary (2026)", 1, t("8:55p"), 156, "STANDARD", True),

    # --- Hoppers (2026)  PG 1h45 ---
    ("Hoppers (2026)",           0, t("1:15p"), 105, "STANDARD", False),
    ("Hoppers (2026)",           0, t("4:00p"), 105, "3D",       False),
    ("Hoppers (2026)",           0, t("6:45p"), 105, "STANDARD", False),
    ("Hoppers (2026)",           1, t("1:15p"), 105, "STANDARD", False),
    ("Hoppers (2026)",           1, t("4:00p"), 105, "3D",       False),

    # --- Broken Bird (2026)  NR 1h39 ---
    ("Broken Bird (2026)",       0, t("1:30p"), 99,  "STANDARD", True),
    ("Broken Bird (2026)",       1, t("1:30p"), 99,  "STANDARD", True),

    # --- Busboys (2026)  R runtime unknown — using 95 min estimate ---
    ("Busboys (2026)",           0, t("3:25p"), 93,  "STANDARD", False),
    ("Busboys (2026)",           1, t("3:25p"), 93,  "STANDARD", False),
]

# ---------------------------------------------------------------------------
# TAGS
# ---------------------------------------------------------------------------
MUST_SEE = {
    "The Silence of the Lambs 35th Anniversary",
    "Speed Racer (2026)",
    "Project Hail Mary (2026)",
    "Hoppers (2026)",
}

HORROR = {
    "Lee Cronin's The Mummy (2026)",
    "Mother Mary (2026)",
    "Over Your Dead Body (2026)",
    "Exit 8 (2025)",
}

SKIP = {
    "Bhooth Bangla (2026)",
    "Strange Journey: The Story of Rocky Horror (2025)",
    "An Evening with Nicole Scherzinger: Live at Royal Albert Hall (2026)",
    "The Blue Angels (2024)",
    "The Super Mario Galaxy Movie (2026)",
    "Michael (2026)",
    "Desert Warrior (2026)",
    "American Youngboy (2026)",
    "I Swear (2026)",
    "Lorne (2026)",
    "Busboys (2026)",
}

# ---------------------------------------------------------------------------
# SCORING
# ---------------------------------------------------------------------------
FORMAT_BONUS = {"IMAX": 2, "PRIME": 1.5, "3D": 0.5, "STANDARD": 0}

def score(title, fmt, recliner):
    s = 100  # base per-film
    if title in MUST_SEE or title in HORROR:
        s += 50
    s += FORMAT_BONUS.get(fmt, 0)
    if recliner:
        s += 1
    return s

# ---------------------------------------------------------------------------
# BRANCH-AND-BOUND
# ---------------------------------------------------------------------------
def fmt_time(mins):
    h, m = divmod(mins, 60)
    ampm = "pm" if h >= 12 else "am"
    h12 = h % 12 or 12
    return f"{h12}:{m:02d}{ampm}"

def solve(showings, top_k=3, min_diff=2, required=None):
    required = required or set()
    # Filter SKIP, sort by (day, start)
    candidates = [s for s in showings if s[0] not in SKIP]
    candidates.sort(key=lambda s: (s[1], s[2]))

    n = len(candidates)

    # Precompute per-candidate score
    scores = [score(c[0], c[4], c[5]) for c in candidates]

    # Suffix max-reachable score per (idx, day_end_0, day_end_1) is too expensive;
    # use a simple suffix sum as upper-bound (ignores feasibility — optimistic)
    suffix_sum = [0] * (n + 1)
    for i in range(n - 1, -1, -1):
        suffix_sum[i] = suffix_sum[i + 1] + scores[i]

    best_schedules = []  # list of (score, schedule_list)

    def hamming(a, b):
        sa, sb = set(id(x) for x in a), set(id(x) for x in b)
        # compare by (title, day, start) tuples instead
        ta = set((x[0], x[1], x[2]) for x in a)
        tb = set((x[0], x[1], x[2]) for x in b)
        return len(ta.symmetric_difference(tb))

    def is_diverse(sched):
        for _, prev in best_schedules:
            if hamming(sched, prev) < min_diff:
                return False
        return True

    def dfs(idx, day_end, used_titles, cur_score, cur_sched):
        # Prune
        upper = cur_score + suffix_sum[idx]
        if best_schedules and upper <= best_schedules[-1][0] and len(best_schedules) >= top_k:
            return

        if idx == n:
            if required and not required.issubset({c[0] for c in cur_sched}):
                return
            if is_diverse(cur_sched):
                entry = (cur_score, list(cur_sched))
                best_schedules.append(entry)
                best_schedules.sort(key=lambda x: -x[0])
                if len(best_schedules) > top_k * 4:
                    best_schedules[top_k * 4:] = []
            return

        c = candidates[idx]
        title, day, start, runtime, fmt, recliner = c

        # Option 1: take it
        if title not in used_titles and start >= day_end[day]:
            new_end = list(day_end)
            new_end[day] = start + runtime - 10
            used_titles.add(title)
            cur_sched.append(c)
            dfs(idx + 1, new_end, used_titles, cur_score + scores[idx], cur_sched)
            cur_sched.pop()
            used_titles.remove(title)

        # Option 2: skip it
        dfs(idx + 1, day_end, used_titles, cur_score, cur_sched)

    dfs(0, [0, 0], set(), 0, [])

    # Return top_k diverse schedules
    result = []
    for sc, sched in best_schedules:
        if len(result) >= top_k:
            break
        if all(hamming(sched, prev) >= min_diff for prev in result):
            result.append(sched)
    # Fallback: if diversity can't be met, just return best
    if not result:
        result = [s for _, s in best_schedules[:top_k]]
    return result

# ---------------------------------------------------------------------------
# OUTPUT
# ---------------------------------------------------------------------------
def print_schedules(schedules):
    day_names = ["Sat Apr 25", "Sun Apr 26"]
    must_sees_total = set(MUST_SEE)

    for i, sched in enumerate(schedules, 1):
        by_day = [[], []]
        for c in sched:
            by_day[c[1]].append(c)

        must_hit = {c[0] for c in sched if c[0] in MUST_SEE}
        horror_count = sum(1 for c in sched if c[0] in HORROR)
        total = len(sched)
        sc = sum(score(c[0], c[4], c[5]) for c in sched)

        print(f"\n=== SCHEDULE {i}  (must-see {len(must_hit)}/{len(must_sees_total)} · films {total} · horror {horror_count} · score {sc:.0f}) ===")
        for d in range(2):
            if not by_day[d]:
                continue
            print(f"\n  {day_names[d]}")
            day_sched = sorted(by_day[d], key=lambda x: x[2])
            for j, c in enumerate(day_sched):
                title, day, start, runtime, fmt, recliner = c
                is_last = (j == len(day_sched) - 1)
                # departure time = walk out at credits; last film show actual end
                end = start + runtime if is_last else start + runtime - 10
                depart_note = "" if is_last else " (depart)"
                tags = []
                if title in MUST_SEE: tags.append("must-see")
                if title in HORROR:   tags.append("horror")
                tag_str = f"  [{', '.join(tags)}]" if tags else ""
                seat = "recliner" if recliner else "standard"
                print(f"    {fmt_time(start)}–{fmt_time(end)}{depart_note}  {title:<45} ({fmt}, {seat}){tag_str}")

    # Report any must-sees missing from ALL schedules
    all_hit = set()
    for sched in schedules:
        all_hit |= {c[0] for c in sched if c[0] in MUST_SEE}
    missed = must_sees_total - all_hit
    if missed:
        print(f"\n  !! DROPPED MUST-SEES (missing from all schedules): {', '.join(missed)}")
    else:
        print(f"\n  All must-sees appear in at least one schedule.")

if __name__ == "__main__":
    import sys
    out = open("output.txt", "w")
    sys.stdout = out
    print_schedules(solve(SHOWINGS))
    out.close()
    sys.stdout = sys.__stdout__
    print("Done. Results in output.txt")
