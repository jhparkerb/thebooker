"""Unit tests for tmdb.py — no network calls."""

import json
import time

import pytest
import requests

import pipeline.tmdb as tmdb


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


def _search_result(title="Foo", year=2026, genre_ids=None, tmdb_id=42):
    return {
        "id": tmdb_id,
        "title": title,
        "release_date": f"{year}-06-01",
        "genre_ids": genre_ids or [],
        "original_language": "en",
    }


def _patch_cache(monkeypatch, tmp_path):
    path = tmp_path / "tmdb.json"
    monkeypatch.setattr(tmdb, "CACHE_PATH", path)
    return path


# ---------------------------------------------------------------------------
# _load_cache / _save_cache
# ---------------------------------------------------------------------------

def test_load_cache_missing_returns_empty(tmp_path, monkeypatch):
    _patch_cache(monkeypatch, tmp_path)
    assert tmdb._load_cache() == {}


def test_save_load_roundtrip(tmp_path, monkeypatch):
    _patch_cache(monkeypatch, tmp_path)
    tmdb._save_cache({"k": {"cached_at": 1.0, "data": {"x": 1}}})
    assert tmdb._load_cache()["k"]["data"] == {"x": 1}


# ---------------------------------------------------------------------------
# lookup — cache behavior
# ---------------------------------------------------------------------------

def test_lookup_cache_miss_then_hit(tmp_path, monkeypatch):
    _patch_cache(monkeypatch, tmp_path)
    calls = []
    def fake_get(path, token, params=None):
        calls.append(path)
        if "keywords" in path:
            return {"keywords": []}
        return {"results": [_search_result()]}
    monkeypatch.setattr(tmdb, "_get", fake_get)

    result1 = tmdb.lookup("Foo", 2026, "tok")
    assert result1["tmdb_id"] == 42
    assert len(calls) == 2       # search + keywords

    calls.clear()
    result2 = tmdb.lookup("Foo", 2026, "tok")
    assert result2["tmdb_id"] == 42
    assert len(calls) == 0       # served from cache


def test_lookup_stale_cache_refetches(tmp_path, monkeypatch):
    cache_file = _patch_cache(monkeypatch, tmp_path)
    cache_file.write_text(json.dumps(
        {"Foo|2026": {"cached_at": 0.0, "data": {"tmdb_id": 1}}}
    ))
    calls = []
    def fake_get(path, token, params=None):
        calls.append(path)
        if "keywords" in path:
            return {"keywords": []}
        return {"results": [_search_result(tmdb_id=99)]}
    monkeypatch.setattr(tmdb, "_get", fake_get)

    result = tmdb.lookup("Foo", 2026, "tok", ttl_days=1)
    assert result["tmdb_id"] == 99
    assert len(calls) == 2


# ---------------------------------------------------------------------------
# lookup — result parsing
# ---------------------------------------------------------------------------

def test_lookup_extracts_fields(tmp_path, monkeypatch):
    _patch_cache(monkeypatch, tmp_path)
    monkeypatch.setattr(tmdb, "_get", lambda path, token, params=None: (
        {"results": [_search_result("Real Title", 2025, [27, 12], 7)]}
        if "search" in path else
        {"keywords": [{"name": "Slasher"}, {"name": "Gore"}]}
    ))
    data = tmdb.lookup("Foo", 2025, "tok")
    assert data["tmdb_id"]         == 7
    assert data["canonical_title"] == "Real Title"
    assert data["year"]            == 2025
    assert data["is_horror"]       is True
    assert 12 in data["genres"]
    assert "slasher" in data["keywords"]


def test_lookup_not_horror_without_genre_27(tmp_path, monkeypatch):
    _patch_cache(monkeypatch, tmp_path)
    monkeypatch.setattr(tmdb, "_get", lambda path, token, params=None: (
        {"results": [_search_result(genre_ids=[18, 35])]}
        if "search" in path else {"keywords": []}
    ))
    assert tmdb.lookup("Foo", 2026, "tok")["is_horror"] is False


def test_lookup_keyword_failure_gives_empty_list(tmp_path, monkeypatch):
    _patch_cache(monkeypatch, tmp_path)
    def fake_get(path, token, params=None):
        if "keywords" in path:
            raise RuntimeError("network down")
        return {"results": [_search_result()]}
    monkeypatch.setattr(tmdb, "_get", fake_get)
    assert tmdb.lookup("Foo", 2026, "tok")["keywords"] == []


def test_lookup_empty_results_retries_without_year(tmp_path, monkeypatch):
    _patch_cache(monkeypatch, tmp_path)
    calls = []
    def fake_get(path, token, params=None):
        calls.append(params)
        return {"results": []}
    monkeypatch.setattr(tmdb, "_get", fake_get)
    result = tmdb.lookup("Foo", 2026, "tok")
    assert result is None
    assert len(calls) == 2
    assert "year" not in calls[1]


def test_lookup_no_year_no_retry(tmp_path, monkeypatch):
    _patch_cache(monkeypatch, tmp_path)
    calls = []
    def fake_get(path, token, params=None):
        calls.append(params)
        return {"results": []}
    monkeypatch.setattr(tmdb, "_get", fake_get)
    result = tmdb.lookup("Foo", None, "tok")
    assert result is None
    assert len(calls) == 1


def test_lookup_search_failure_returns_none(tmp_path, monkeypatch, capsys):
    _patch_cache(monkeypatch, tmp_path)
    def raises(*a, **kw):
        raise RuntimeError("conn refused")
    monkeypatch.setattr(tmdb, "_get", raises)
    result = tmdb.lookup("Foo", 2026, "tok")
    assert result is None
    assert "tmdb" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# _get — retry / rate-limit behavior
# ---------------------------------------------------------------------------

def _fake_session(responses):
    it = iter(responses)
    class FakeSession:
        def get(self, *args, **kwargs):
            return next(it)
    return FakeSession


def test_get_429_then_200(monkeypatch):
    monkeypatch.setattr(requests, "Session", _fake_session([_Resp(429), _Resp(200, {"ok": True})]))
    monkeypatch.setattr(time, "sleep", lambda *_: None)
    assert tmdb._get("/test", "tok") == {"ok": True}


def test_get_three_429s_raises(monkeypatch):
    monkeypatch.setattr(requests, "Session", _fake_session([_Resp(429), _Resp(429), _Resp(429)]))
    monkeypatch.setattr(time, "sleep", lambda *_: None)
    with pytest.raises(RuntimeError, match="rate limit"):
        tmdb._get("/test", "tok")
