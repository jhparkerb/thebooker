"""Unit tests for pipeline.py pure helpers — no I/O, no network."""

import datetime

from pipeline.pipeline import _weekend_days, _scoring_cfg
from pipeline.optimizer import ScoringConfig


# --- _weekend_days ---

def test_weekend_days_returns_two_days():
    result = _weekend_days(datetime.date(2026, 5, 4))  # Monday
    assert len(result) == 2

def test_weekend_days_are_saturday_sunday():
    sat, sun = _weekend_days(datetime.date(2026, 5, 4))
    assert sat.weekday() == 5   # Saturday
    assert sun.weekday() == 6   # Sunday

def test_weekend_days_consecutive():
    sat, sun = _weekend_days(datetime.date(2026, 5, 4))
    assert sun == sat + datetime.timedelta(days=1)

def test_weekend_days_from_saturday_is_same_day():
    sat, _ = _weekend_days(datetime.date(2026, 5, 2))   # already Saturday
    assert sat == datetime.date(2026, 5, 2)

def test_weekend_days_from_friday_is_next_day():
    sat, _ = _weekend_days(datetime.date(2026, 5, 1))   # Friday
    assert sat == datetime.date(2026, 5, 2)

def test_weekend_days_from_sunday_jumps_to_next_saturday():
    # Sunday is "after" this weekend; next opportunity is following Saturday
    sat, _ = _weekend_days(datetime.date(2026, 5, 3))   # Sunday May 3
    assert sat == datetime.date(2026, 5, 9)


# --- _scoring_cfg ---

def test_scoring_cfg_empty_config_gives_defaults():
    cfg = _scoring_cfg({})
    assert isinstance(cfg, ScoringConfig)
    assert cfg.base_per_film  == 100.0
    assert cfg.must_see_bonus == 50.0
    assert cfg.horror_bonus   == 30.0

def test_scoring_cfg_override_single_field():
    cfg = _scoring_cfg({"scoring": {"base_per_film": 200.0}})
    assert cfg.base_per_film  == 200.0
    assert cfg.must_see_bonus == 50.0   # default unchanged

def test_scoring_cfg_unknown_keys_ignored():
    cfg = _scoring_cfg({"scoring": {"base_per_film": 50.0, "invented_key": 999}})
    assert cfg.base_per_film == 50.0
    assert cfg.must_see_bonus == 50.0   # other fields still default

def test_scoring_cfg_no_scoring_section():
    cfg = _scoring_cfg({"tmdb": {"read_access_token": "x"}})
    assert cfg.base_per_film == 100.0
