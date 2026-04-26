"""Unit tests for digest.py helper functions."""

from datetime import date

from pipeline.digest import _fmt_time, _showing_tags, _day_summary
from pipeline.optimizer import Showing, TagSets


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
