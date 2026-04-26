"""Unit tests for letterboxd.py — no network calls."""

import json
import time

import pytest

import pipeline.letterboxd as lb


# ---------------------------------------------------------------------------
# _parse_display_name
# ---------------------------------------------------------------------------

def test_parse_display_name_with_year():
    assert lb._parse_display_name("Coyote vs. ACME (2026)") == ("Coyote vs. ACME", 2026)

def test_parse_display_name_no_year():
    title, year = lb._parse_display_name("Foo")
    assert title == "Foo"
    assert year is None

def test_parse_display_name_strips_whitespace():
    title, year = lb._parse_display_name("  Foo (2025)  ")
    assert title == "Foo"
    assert year == 2025


# ---------------------------------------------------------------------------
# _has_next_page
# ---------------------------------------------------------------------------

def test_has_next_page_query_param_form():
    assert lb._has_next_page('href="?page=3"', 2) is True

def test_has_next_page_path_form():
    assert lb._has_next_page("/page/3/", 2) is True

def test_has_next_page_absent():
    assert lb._has_next_page("no link here", 2) is False


# ---------------------------------------------------------------------------
# _PosterParser
# ---------------------------------------------------------------------------

_POSTER_HTML = (
    '<div class="react-component" data-component-class="LazyPoster"'
    ' data-item-name="Foo (2026)" data-item-slug="foo"></div>'
)

def test_poster_parser_basic():
    p = lb._PosterParser()
    p.feed(_POSTER_HTML)
    assert len(p.films) == 1
    f = p.films[0]
    assert f["title"] == "Foo"
    assert f["year"]  == 2026
    assert f["slug"]  == "foo"

def test_poster_parser_fallback_to_full_display_name():
    html = (
        '<div class="react-component" data-component-class="LazyPoster"'
        ' data-item-full-display-name="Bar (2025)" data-item-slug="bar"></div>'
    )
    p = lb._PosterParser()
    p.feed(html)
    assert p.films[0]["title"] == "Bar"
    assert p.films[0]["year"]  == 2025

def test_poster_parser_ignores_non_lazyposter():
    html = '<div class="react-component" data-component-class="OtherWidget" data-item-name="X (2025)"></div>'
    p = lb._PosterParser()
    p.feed(html)
    assert p.films == []

def test_poster_parser_ignores_non_div():
    html = '<span data-component-class="LazyPoster" data-item-name="X (2025)"></span>'
    p = lb._PosterParser()
    p.feed(html)
    assert p.films == []

def test_poster_parser_no_slug_no_title_skipped():
    html = '<div class="react-component" data-component-class="LazyPoster"></div>'
    p = lb._PosterParser()
    p.feed(html)
    assert p.films == []

def test_poster_parser_multiple_entries():
    html = (
        '<div class="react-component" data-component-class="LazyPoster"'
        ' data-item-name="A (2026)" data-item-slug="a"></div>'
        '<div class="react-component" data-component-class="LazyPoster"'
        ' data-item-name="B (2025)" data-item-slug="b"></div>'
    )
    p = lb._PosterParser()
    p.feed(html)
    assert len(p.films) == 2


# ---------------------------------------------------------------------------
# _scrape_list
# ---------------------------------------------------------------------------

def _page_html(titles_years, page_num, has_next=True):
    parts = []
    for title, year in titles_years:
        parts.append(
            f'<div class="react-component" data-component-class="LazyPoster"'
            f' data-item-name="{title} ({year})" data-item-slug="{title.lower()}"></div>'
        )
    if has_next:
        parts.append(f'href="?page={page_num + 1}"')
    return "".join(parts)


def test_scrape_list_collects_multiple_pages(monkeypatch):
    pages = [
        _page_html([("A", 2026), ("B", 2026)], 1),
        _page_html([("C", 2026)], 2),
        "",  # empty → stop
    ]
    it = iter(pages)
    monkeypatch.setattr(lb, "_fetch_page", lambda url: next(it))
    monkeypatch.setattr(time, "sleep", lambda *_: None)
    films = lb._scrape_list("http://x.com/{page}")
    assert [f["title"] for f in films] == ["A", "B", "C"]


def test_scrape_list_stop_before_year(monkeypatch):
    pages = [
        _page_html([("New", 2026)], 1),
        _page_html([("Old", 2019)], 2, has_next=False),
    ]
    it = iter(pages)
    monkeypatch.setattr(lb, "_fetch_page", lambda url: next(it))
    monkeypatch.setattr(time, "sleep", lambda *_: None)
    # Page 2 has no films >= 2025 → break after adding it
    films = lb._scrape_list("http://x.com/{page}", stop_before_year=2025)
    titles = [f["title"] for f in films]
    assert "New" in titles
    assert "Old" in titles   # already extended before the early-stop check fires


def test_scrape_list_stops_when_no_next_page(monkeypatch):
    pages = [_page_html([("A", 2026)], 1, has_next=False)]
    it = iter(pages)
    monkeypatch.setattr(lb, "_fetch_page", lambda url: next(it))
    monkeypatch.setattr(time, "sleep", lambda *_: None)
    films = lb._scrape_list("http://x.com/{page}")
    assert len(films) == 1 and films[0]["title"] == "A"


# ---------------------------------------------------------------------------
# _read_watched_csv
# ---------------------------------------------------------------------------

def test_read_watched_csv_basic(tmp_path):
    f = tmp_path / "watched.csv"
    f.write_text(
        "Date,Name,Year,Letterboxd URI,Rating\n"
        "2026-01-01,Foo,2025,https://letterboxd.com/film/foo/,4\n"
        "2026-02-01,Bar,2024,https://letterboxd.com/film/bar/,3\n"
    )
    films = lb._read_watched_csv(f)
    assert len(films) == 2
    assert films[0] == {"slug": "foo", "title": "Foo", "year": 2025}
    assert films[1]["slug"] == "bar"

def test_read_watched_csv_non_numeric_year(tmp_path):
    f = tmp_path / "watched.csv"
    f.write_text(
        "Date,Name,Year,Letterboxd URI,Rating\n"
        "2026-01-01,Foo,,https://letterboxd.com/film/foo/,\n"
    )
    assert lb._read_watched_csv(f)[0]["year"] is None

def test_read_watched_csv_empty_title_skipped(tmp_path):
    f = tmp_path / "watched.csv"
    f.write_text(
        "Date,Name,Year,Letterboxd URI,Rating\n"
        "2026-01-01,,2025,https://letterboxd.com/film/x/,\n"
    )
    assert lb._read_watched_csv(f) == []


# ---------------------------------------------------------------------------
# fetch_watchlist — cache hit / miss / force / TTL
# ---------------------------------------------------------------------------

def _patch_lb_cache(monkeypatch, tmp_path):
    path = tmp_path / "lb.json"
    monkeypatch.setattr(lb, "CACHE_PATH", path)
    return path


def _single_film_page(title="A", year=2026):
    return (
        f'<div class="react-component" data-component-class="LazyPoster"'
        f' data-item-name="{title} ({year})" data-item-slug="{title.lower()}"></div>'
    )


def test_fetch_watchlist_cache_miss_writes_cache(tmp_path, monkeypatch):
    cache_file = _patch_lb_cache(monkeypatch, tmp_path)
    monkeypatch.setattr(lb, "_fetch_page", lambda url: _single_film_page())
    monkeypatch.setattr(time, "sleep", lambda *_: None)
    films = lb.fetch_watchlist("user1")
    assert any(f["title"] == "A" for f in films)
    assert cache_file.exists()


def test_fetch_watchlist_cache_hit_skips_network(tmp_path, monkeypatch):
    cache_file = _patch_lb_cache(monkeypatch, tmp_path)
    cache_file.write_text(json.dumps({
        "user1:watchlist": {"cached_at": time.time(), "films": [{"slug": "x", "title": "X", "year": 2026}]}
    }))
    fetched = []
    monkeypatch.setattr(lb, "_fetch_page", lambda url: fetched.append(url) or "")
    films = lb.fetch_watchlist("user1")
    assert films == [{"slug": "x", "title": "X", "year": 2026}]
    assert not fetched


def test_fetch_watchlist_force_bypasses_cache(tmp_path, monkeypatch):
    cache_file = _patch_lb_cache(monkeypatch, tmp_path)
    cache_file.write_text(json.dumps({
        "user1:watchlist": {"cached_at": time.time(), "films": [{"slug": "old", "title": "Old", "year": 2026}]}
    }))
    fetched = []
    monkeypatch.setattr(lb, "_fetch_page", lambda url: fetched.append(url) or "")
    monkeypatch.setattr(time, "sleep", lambda *_: None)
    lb.fetch_watchlist("user1", force=True)
    assert fetched


def test_fetch_watchlist_stale_cache_refetches(tmp_path, monkeypatch):
    cache_file = _patch_lb_cache(monkeypatch, tmp_path)
    cache_file.write_text(json.dumps({"user1:watchlist": {"cached_at": 0.0, "films": []}}))
    fetched = []
    monkeypatch.setattr(lb, "_fetch_page", lambda url: fetched.append(url) or "")
    monkeypatch.setattr(time, "sleep", lambda *_: None)
    lb.fetch_watchlist("user1")
    assert fetched


# ---------------------------------------------------------------------------
# fetch_watched — csv_path bypasses network entirely
# ---------------------------------------------------------------------------

def test_fetch_watched_with_csv_path(tmp_path):
    csv_file = tmp_path / "watched.csv"
    csv_file.write_text(
        "Date,Name,Year,Letterboxd URI,Rating\n"
        "2026-01-01,Foo,2025,https://letterboxd.com/film/foo/,\n"
    )
    films = lb.fetch_watched("user1", csv_path=csv_file)
    assert len(films) == 1
    assert films[0]["title"] == "Foo"


def test_fetch_watched_no_csv_uses_cache(tmp_path, monkeypatch):
    cache_file = _patch_lb_cache(monkeypatch, tmp_path)
    cache_file.write_text(json.dumps({
        "user1:watched": {"cached_at": time.time(), "films": [{"slug": "w", "title": "W", "year": 2024}]}
    }))
    monkeypatch.setattr(lb, "_fetch_page", lambda url: (_ for _ in ()).throw(AssertionError("unexpected network call")))
    films = lb.fetch_watched("user1")
    assert films[0]["title"] == "W"
