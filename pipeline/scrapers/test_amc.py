"""Unit tests for scrapers/amc.py — no network calls."""

import json
import time
from datetime import date

import pytest
import requests

import pipeline.scrapers.amc as amc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _Resp:
    def __init__(self, status, data=None):
        self.status_code = status
        self._data = data or {}
    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")
    def json(self):
        return self._data


def _showtime_entry(title="Foo", runtime=120, dt="2026-05-09T10:00:00", attrs=None):
    return {
        "movieName": title,
        "runTime": runtime,
        "showDateTimes": [{"showDateTimeLocal": dt, "attributes": attrs or []}],
    }


# ---------------------------------------------------------------------------
# _parse_time
# ---------------------------------------------------------------------------

def test_parse_time_afternoon():
    assert amc._parse_time("2026-04-25T14:30:00") == 870

def test_parse_time_midnight():
    assert amc._parse_time("2026-04-25T00:00:00") == 0

def test_parse_time_late_night():
    assert amc._parse_time("2026-04-25T23:59:00") == 1439


# ---------------------------------------------------------------------------
# _parse_format_recliner
# ---------------------------------------------------------------------------

def test_parse_format_default_standard():
    fmt, recliner = amc._parse_format_recliner([])
    assert fmt == "STANDARD"
    assert recliner is False

def test_parse_format_imax():
    fmt, _ = amc._parse_format_recliner([{"code": "IMAX"}])
    assert fmt == "IMAX"

def test_parse_format_plf_maps_to_imax():
    fmt, _ = amc._parse_format_recliner([{"code": "PLF"}])
    assert fmt == "IMAX"

def test_parse_format_dolby_sets_recliner():
    fmt, recliner = amc._parse_format_recliner([{"code": "DOLBY"}])
    assert fmt == "DOLBY"
    assert recliner is True

def test_parse_format_prime_sets_recliner():
    fmt, recliner = amc._parse_format_recliner([{"code": "PRIME"}])
    assert fmt == "PRIME"
    assert recliner is True

def test_parse_format_reserve_recliner_only():
    fmt, recliner = amc._parse_format_recliner([{"code": "RESERVE"}])
    assert fmt == "STANDARD"
    assert recliner is True

def test_parse_format_3d():
    fmt, recliner = amc._parse_format_recliner([{"code": "3D"}])
    assert fmt == "3D"
    assert recliner is False

def test_parse_format_lowercase_code():
    fmt, _ = amc._parse_format_recliner([{"code": "imax"}])
    assert fmt == "IMAX"


# ---------------------------------------------------------------------------
# find_theater_id
# ---------------------------------------------------------------------------

def test_find_theater_id_basic(monkeypatch):
    monkeypatch.setattr(amc, "_get", lambda path, params=None: {
        "_embedded": {"theatres": [{"id": "123", "name": "AMC Foo", "slug": "amc-foo"}]}
    })
    result = amc.find_theater_id("Foo")
    assert result == [{"id": "123", "name": "AMC Foo", "slug": "amc-foo"}]

def test_find_theater_id_missing_slug_defaults_empty(monkeypatch):
    monkeypatch.setattr(amc, "_get", lambda path, params=None: {
        "_embedded": {"theatres": [{"id": "1", "name": "X"}]}
    })
    assert amc.find_theater_id("X")[0]["slug"] == ""

def test_find_theater_id_missing_embedded_returns_empty(monkeypatch):
    monkeypatch.setattr(amc, "_get", lambda path, params=None: {})
    assert amc.find_theater_id("X") == []


# ---------------------------------------------------------------------------
# fetch_raw — cache hit / miss / force
# ---------------------------------------------------------------------------

def test_fetch_raw_cache_miss_writes_file(tmp_path, monkeypatch):
    monkeypatch.setattr(amc, "CACHE_DIR", tmp_path)
    payload = {"_embedded": {"showtimes": []}}
    monkeypatch.setattr(amc, "_get", lambda path, params=None: payload)
    result = amc.fetch_raw("t1", date(2026, 5, 9))
    assert result == payload
    assert (tmp_path / "t1_2026-05-09.json").exists()

def test_fetch_raw_cache_hit_skips_network(tmp_path, monkeypatch):
    monkeypatch.setattr(amc, "CACHE_DIR", tmp_path)
    payload = {"_embedded": {"showtimes": []}}
    (tmp_path / "t1_2026-05-09.json").write_text(json.dumps(payload))
    calls = []
    monkeypatch.setattr(amc, "_get", lambda *a, **kw: calls.append(1) or {})
    amc.fetch_raw("t1", date(2026, 5, 9))
    assert not calls

def test_fetch_raw_force_refetches(tmp_path, monkeypatch):
    monkeypatch.setattr(amc, "CACHE_DIR", tmp_path)
    stale = {"old": True}
    (tmp_path / "t1_2026-05-09.json").write_text(json.dumps(stale))
    payload = {"_embedded": {"showtimes": []}}
    calls = []
    def fake_get(path, params=None):
        calls.append(1)
        return payload
    monkeypatch.setattr(amc, "_get", fake_get)
    result = amc.fetch_raw("t1", date(2026, 5, 9), force=True)
    assert calls
    assert result == payload


# ---------------------------------------------------------------------------
# AMCScraper.fetch
# ---------------------------------------------------------------------------

def test_scraper_fetch_basic(tmp_path, monkeypatch):
    monkeypatch.setattr(amc, "CACHE_DIR", tmp_path)
    day = date(2026, 5, 9)
    payload = {"_embedded": {"showtimes": [_showtime_entry()]}}
    monkeypatch.setattr(amc, "_get", lambda *a, **kw: payload)
    showings = amc.AMCScraper("t1", "Test Theater").fetch("t1", day)
    assert len(showings) == 1
    s = showings[0]
    assert s.title_raw         == "Foo"
    assert s.runtime_min       == 120
    assert s.listed_start_min  == 600   # 10:00 → 600 min
    assert s.day               == day
    assert s.theater_id        == "t1"
    assert s.format            == "STANDARD"
    assert s.has_recliner      is False

def test_scraper_fetch_drops_empty_title(tmp_path, monkeypatch):
    monkeypatch.setattr(amc, "CACHE_DIR", tmp_path)
    payload = {"_embedded": {"showtimes": [_showtime_entry(title="")]}}
    monkeypatch.setattr(amc, "_get", lambda *a, **kw: payload)
    assert amc.AMCScraper("t1", "T").fetch("t1", date(2026, 5, 9)) == []

def test_scraper_fetch_drops_zero_runtime(tmp_path, monkeypatch):
    monkeypatch.setattr(amc, "CACHE_DIR", tmp_path)
    payload = {"_embedded": {"showtimes": [_showtime_entry(runtime=0)]}}
    monkeypatch.setattr(amc, "_get", lambda *a, **kw: payload)
    assert amc.AMCScraper("t1", "T").fetch("t1", date(2026, 5, 9)) == []

def test_scraper_fetch_skips_missing_datetime(tmp_path, monkeypatch):
    monkeypatch.setattr(amc, "CACHE_DIR", tmp_path)
    payload = {"_embedded": {"showtimes": [{
        "movieName": "Foo", "runTime": 90,
        "showDateTimes": [{"showDateTimeLocal": "", "attributes": []}],
    }]}}
    monkeypatch.setattr(amc, "_get", lambda *a, **kw: payload)
    assert amc.AMCScraper("t1", "T").fetch("t1", date(2026, 5, 9)) == []

def test_scraper_fetch_imax_and_recliner(tmp_path, monkeypatch):
    monkeypatch.setattr(amc, "CACHE_DIR", tmp_path)
    payload = {"_embedded": {"showtimes": [
        _showtime_entry(attrs=[{"code": "IMAX"}, {"code": "RESERVE"}])
    ]}}
    monkeypatch.setattr(amc, "_get", lambda *a, **kw: payload)
    s = amc.AMCScraper("t1", "T").fetch("t1", date(2026, 5, 9))[0]
    assert s.format       == "IMAX"
    assert s.has_recliner is True

def test_scraper_fetch_legacy_no_showdatetimes(tmp_path, monkeypatch):
    # When showDateTimes key is absent, the movie dict itself acts as a single showtime
    monkeypatch.setattr(amc, "CACHE_DIR", tmp_path)
    payload = {"_embedded": {"showtimes": [{
        "movieName": "Bar", "runTime": 100,
        "showDateTimeLocal": "2026-05-09T14:00:00",
        "attributes": [],
    }]}}
    monkeypatch.setattr(amc, "_get", lambda *a, **kw: payload)
    showings = amc.AMCScraper("t1", "T").fetch("t1", date(2026, 5, 9))
    assert len(showings) == 1
    assert showings[0].title_raw          == "Bar"
    assert showings[0].listed_start_min   == 840   # 14:00


# ---------------------------------------------------------------------------
# _get — retry / rate-limit behavior
# ---------------------------------------------------------------------------

def _fake_session(responses):
    it = iter(responses)
    class FakeSession:
        def __init__(self):
            self.headers = {}
        def get(self, *args, **kwargs):
            return next(it)
    return FakeSession


def test_get_429_then_200(monkeypatch):
    monkeypatch.setattr(requests, "Session", _fake_session([_Resp(429), _Resp(200, {"data": "ok"})]))
    monkeypatch.setattr(time, "sleep", lambda *_: None)
    monkeypatch.setattr(amc, "_cfg", lambda: {"amc": {"vendor_key": "test"}})
    assert amc._get("/path") == {"data": "ok"}

def test_get_three_429s_raises(monkeypatch):
    monkeypatch.setattr(requests, "Session", _fake_session([_Resp(429), _Resp(429), _Resp(429)]))
    monkeypatch.setattr(time, "sleep", lambda *_: None)
    monkeypatch.setattr(amc, "_cfg", lambda: {"amc": {"vendor_key": "test"}})
    with pytest.raises(RuntimeError, match="rate limit"):
        amc._get("/path")
