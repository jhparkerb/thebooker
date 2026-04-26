"""Unit tests for pipeline.run() and main() — no I/O, no network."""

import datetime
import sys

import pytest

import pipeline.digest
import pipeline.pipeline as pp
from pipeline.optimizer import Showing, TagSets


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TODAY = datetime.date(2026, 5, 9)
_DAYS  = [_TODAY, _TODAY + datetime.timedelta(days=1)]

_CFG = {
    "tmdb":       {"read_access_token": "tok", "cache_ttl_days": 30},
    "letterboxd": {"username": "user1"},
    "theaters":   [{"id": "t1", "chain": "amc", "chain_id": "123", "name": "Test AMC"}],
}

_EMPTY_TAGS = TagSets(must_see=set(), horror=set(), skip=set())


def _showing(title="Foo", start=600, runtime=90):
    return Showing(title, title, None, 2026, "t1", _TODAY, start, runtime, "STANDARD", False)


def _setup_run(monkeypatch, showings=None, tags=None):
    """Patch all external I/O so run() can execute end-to-end."""
    showings = showings if showings is not None else [_showing()]
    tags     = tags or _EMPTY_TAGS

    class FakeScraper:
        def fetch(self, theater_id, day):
            return showings

    monkeypatch.setattr(pp, "_make_scraper",  lambda cfg: FakeScraper())
    monkeypatch.setattr(pp, "build_tag_sets", lambda cfg, titles: tags)
    monkeypatch.setattr(pipeline.digest, "render", lambda *a, **kw: None)


# ---------------------------------------------------------------------------
# _load_cfg
# ---------------------------------------------------------------------------

def test_load_cfg_reads_yaml(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("key: value\n")
    monkeypatch.setattr(pp, "CONFIG", cfg_file)
    assert pp._load_cfg() == {"key": "value"}


# ---------------------------------------------------------------------------
# run()
# ---------------------------------------------------------------------------

def test_run_calls_render(monkeypatch):
    rendered = []
    _setup_run(monkeypatch)
    monkeypatch.setattr(pipeline.digest, "render", lambda *a, **kw: rendered.append(a))
    pp.run(_CFG, _DAYS)
    assert rendered

def test_run_skips_unknown_chain(monkeypatch, capsys):
    cfg = {**_CFG, "theaters": [{"id": "t1", "chain": "regal", "chain_id": "x", "name": "Regal"}]}
    monkeypatch.setattr(pp, "build_tag_sets", lambda cfg, titles: _EMPTY_TAGS)
    monkeypatch.setattr(pipeline.digest, "render", lambda *a, **kw: None)
    pp.run(cfg, _DAYS)
    assert "skipping" in capsys.readouterr().err

def test_run_handles_scraper_fetch_error(monkeypatch, capsys):
    class ErrorScraper:
        def fetch(self, theater_id, day):
            raise RuntimeError("network down")
    monkeypatch.setattr(pp, "_make_scraper",  lambda cfg: ErrorScraper())
    monkeypatch.setattr(pp, "build_tag_sets", lambda cfg, titles: _EMPTY_TAGS)
    monkeypatch.setattr(pipeline.digest, "render", lambda *a, **kw: None)
    pp.run(_CFG, _DAYS)
    assert "network down" in capsys.readouterr().err

def test_run_excludes_theater_with_no_showings(monkeypatch):
    rendered_results = []
    class EmptyScraper:
        def fetch(self, theater_id, day):
            return []
    monkeypatch.setattr(pp, "_make_scraper",  lambda cfg: EmptyScraper())
    monkeypatch.setattr(pp, "build_tag_sets", lambda cfg, titles: _EMPTY_TAGS)
    monkeypatch.setattr(pipeline.digest, "render",
                        lambda results, *a, **kw: rendered_results.extend(results))
    pp.run(_CFG, _DAYS)
    assert rendered_results == []

def test_run_results_sorted_by_score_descending(monkeypatch):
    cfg = {**_CFG, "theaters": [
        {"id": "t1", "chain": "amc", "chain_id": "1", "name": "A"},
        {"id": "t2", "chain": "amc", "chain_id": "2", "name": "B"},
    ]}

    call_count = [0]
    def make_scraper(tcfg):
        call_count[0] += 1
        class S:
            def fetch(self, theater_id, day):
                return [_showing()]
        return S()

    captured = []
    monkeypatch.setattr(pp, "_make_scraper",  make_scraper)
    monkeypatch.setattr(pp, "build_tag_sets", lambda cfg, titles: _EMPTY_TAGS)
    monkeypatch.setattr(pipeline.digest, "render",
                        lambda results, *a, **kw: captured.extend(results))
    pp.run(cfg, _DAYS)
    scores = [score for _, _, score in captured]
    assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def test_main_calls_run(monkeypatch):
    calls = []
    monkeypatch.setattr(sys, "argv", ["pipeline"])
    monkeypatch.setattr(pp, "_load_cfg",  lambda: _CFG)
    monkeypatch.setattr(pp, "run", lambda cfg, days: calls.append((cfg, days)))
    pp.main()
    assert calls
    cfg, days = calls[0]
    assert cfg == _CFG
    assert len(days) == 2

def test_main_passes_date_arg(monkeypatch):
    calls = []
    monkeypatch.setattr(sys, "argv", ["pipeline", "--date", "2026-05-04"])
    monkeypatch.setattr(pp, "_load_cfg", lambda: _CFG)
    monkeypatch.setattr(pp, "run", lambda cfg, days: calls.append(days))
    pp.main()
    sat, sun = calls[0]
    assert sat == datetime.date(2026, 5, 9)   # next Saturday after May 4
    assert sun == datetime.date(2026, 5, 10)
