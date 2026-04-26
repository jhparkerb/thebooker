"""Unit tests for digest.py helper functions."""

import io
import sys
from datetime import date

from pipeline.digest import (
    _fmt_time, _showing_tags, _day_summary,
    _end_min, _schedule_header, _dropped_must_sees, render,
)
from pipeline.optimizer import Showing, TagSets, ScoringConfig


def _s(title, fmt="STANDARD", recliner=False, tmdb_id=None):
    return Showing(title, title, tmdb_id, 2026, "t1",
                   date(2026, 5, 9), 600, 90, fmt, recliner)


EMPTY_TAGS = TagSets(must_see=set(), horror=set(), skip=set())


# --- _fmt_time ---

def test_fmt_time_midnight():
    assert _fmt_time(0) == "12:00am"

def test_fmt_time_noon():
    assert _fmt_time(720) == "12:00pm"

def test_fmt_time_morning():
    assert _fmt_time(90) == "1:30am"

def test_fmt_time_afternoon():
    assert _fmt_time(810) == "1:30pm"

def test_fmt_time_late_night():
    assert _fmt_time(1320) == "10:00pm"


# --- _showing_tags ---

def test_showing_tags_empty():
    assert _showing_tags(_s("Foo"), EMPTY_TAGS) == ""

def test_showing_tags_must_see_by_title():
    tags = TagSets(must_see={"Foo"}, horror=set(), skip=set())
    assert "must-see" in _showing_tags(_s("Foo"), tags)

def test_showing_tags_must_see_by_tmdb_id():
    tags = TagSets(must_see={99}, horror=set(), skip=set())
    assert "must-see" in _showing_tags(_s("Foo", tmdb_id=99), tags)

def test_showing_tags_horror():
    tags = TagSets(must_see=set(), horror={"Foo"}, skip=set())
    assert "horror" in _showing_tags(_s("Foo"), tags)

def test_showing_tags_imax_format():
    assert "IMAX" in _showing_tags(_s("Foo", fmt="IMAX"), EMPTY_TAGS)

def test_showing_tags_standard_format_omitted():
    # must-see so the result is non-empty, confirming STANDARD is specifically excluded
    tags = TagSets(must_see={"Foo"}, horror=set(), skip=set())
    result = _showing_tags(_s("Foo", fmt="STANDARD"), tags)
    assert result != ""
    assert "STANDARD" not in result

def test_showing_tags_recliner():
    assert "recliner" in _showing_tags(_s("Foo", recliner=True), EMPTY_TAGS)

def test_showing_tags_combined():
    tags = TagSets(must_see={"Bar"}, horror={"Bar"}, skip=set())
    result = _showing_tags(_s("Bar", fmt="DOLBY", recliner=True), tags)
    assert "must-see" in result
    assert "horror" in result
    assert "DOLBY" in result
    assert "recliner" in result


# --- _day_summary ---

def test_day_summary_plural():
    assert "2 films" in _day_summary([_s("A"), _s("B")], EMPTY_TAGS)

def test_day_summary_singular():
    assert "1 film" in _day_summary([_s("A")], EMPTY_TAGS)

def test_day_summary_no_must_see_label_when_zero():
    summary = _day_summary([_s("A"), _s("B")], EMPTY_TAGS)
    assert "must-see" not in summary

def test_day_summary_must_see_count():
    tags = TagSets(must_see={"A"}, horror=set(), skip=set())
    summary = _day_summary([_s("A"), _s("B")], tags)
    assert "1 must-see" in summary

def test_day_summary_horror_count():
    tags = TagSets(must_see=set(), horror={"A", "B"}, skip=set())
    summary = _day_summary([_s("A"), _s("B"), _s("C")], tags)
    assert "2 horror" in summary


# --- _end_min ---

def test_end_min_last_film_full_runtime():
    s = _s("Foo")
    end, is_depart = _end_min(s, is_last=True)
    assert end == s.listed_start_min + s.runtime_min
    assert not is_depart

def test_end_min_non_last_film_departs_early():
    s = _s("Foo")
    end, is_depart = _end_min(s, is_last=False)
    assert end == s.listed_start_min + s.runtime_min - 10
    assert is_depart


# --- _schedule_header ---

def test_schedule_header_counts():
    tags = TagSets(must_see={"A", "B", "C", "D"}, horror={"A"}, skip=set())
    sched = [_s("A"), _s("B"), _s("Z")]
    h = _schedule_header(sched, tags, 650.0, must_see_total=4)
    assert "must-see 2/4" in h
    assert "horror 1" in h
    assert "films 3" in h
    assert "score 650" in h

def test_schedule_header_zero_horror():
    tags = TagSets(must_see=set(), horror=set(), skip=set())
    h = _schedule_header([_s("X")], tags, 100.0, must_see_total=0)
    assert "horror 0" in h


# --- _dropped_must_sees ---

def test_dropped_must_sees_none_missing():
    tags = TagSets(must_see={"A"}, horror=set(), skip=set())
    assert _dropped_must_sees([[_s("A")]], tags) == set()

def test_dropped_must_sees_one_missing():
    tags = TagSets(must_see={"A", "B"}, horror=set(), skip=set())
    assert _dropped_must_sees([[_s("A")]], tags) == {"B"}

def test_dropped_must_sees_empty_must_see():
    tags = TagSets(must_see=set(), horror=set(), skip=set())
    assert _dropped_must_sees([[_s("A")]], tags) == set()

def test_dropped_must_sees_across_multiple_schedules():
    tags = TagSets(must_see={"A", "B"}, horror=set(), skip=set())
    # A in sched 1, B in sched 2 — both covered
    assert _dropped_must_sees([[_s("A")], [_s("B")]], tags) == set()


# --- render() integration ---

def _capture(fn):
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        fn()
    finally:
        sys.stdout = old
    return buf.getvalue()

def _two_showings_result():
    """Two showings on the same day; Film A starts first."""
    d = date(2026, 5, 9)
    tags = TagSets(must_see={"A"}, horror=set(), skip=set())
    a = Showing("A", "A", None, 2026, "t1", d, 600, 90, "STANDARD", False)   # 10am, 90min
    b = Showing("B", "B", None, 2026, "t1", d, 705, 90, "STANDARD", False)   # 11:45am, 90min
    sched = [a, b]
    scored = [(sched, 200.0)]
    theater_cfg = {"name": "Test Theater"}
    return [(theater_cfg, scored, 200.0)], tags, [d]

def test_render_departure_note_on_non_final():
    results, tags, days = _two_showings_result()
    out = _capture(lambda: render(results, tags, days, {}))
    assert "(depart)" in out

def test_render_no_departure_note_on_final():
    results, tags, days = _two_showings_result()
    lines = _capture(lambda: render(results, tags, days, {})).splitlines()
    # The line for Film B (last) should NOT contain "(depart)"
    b_lines = [l for l in lines if "B" in l and "depart" in l]
    assert not b_lines

def test_render_schedule_header_present():
    results, tags, days = _two_showings_result()
    out = _capture(lambda: render(results, tags, days, {}))
    assert "must-see" in out
    assert "score" in out

def test_render_dropped_must_see_warning():
    results, tags, days = _two_showings_result()
    # Override tags so must_see includes something not in any schedule
    tags2 = TagSets(must_see={"A", "Missing Film"}, horror=set(), skip=set())
    out = _capture(lambda: render(results, tags2, days, {}))
    assert "DROPPED MUST-SEES" in out

def test_render_all_must_sees_present_message():
    results, tags, days = _two_showings_result()
    out = _capture(lambda: render(results, tags, days, {}))
    assert "All must-sees appear" in out
