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
# _fetch_watched_rss
# ---------------------------------------------------------------------------

def _rss(items_xml=""):
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<rss xmlns:letterboxd="https://letterboxd.com" xmlns:tmdb="https://themoviedb.org">'
        f'<channel>{items_xml}</channel></rss>'
    )

def _rss_item(title="Foo", year="2026", tmdb_id="123", slug="foo"):
    return (
        f"<item>"
        f"<title>{title}, {year}</title>"
        f"<link>https://letterboxd.com/jhparkerb/film/{slug}/</link>"
        f"<letterboxd:filmTitle>{title}</letterboxd:filmTitle>"
        f"<letterboxd:filmYear>{year}</letterboxd:filmYear>"
        f"<tmdb:movieId>{tmdb_id}</tmdb:movieId>"
        f"</item>"
    )


def test_fetch_watched_rss_extracts_fields(monkeypatch):
    monkeypatch.setattr(lb, "_fetch_page", lambda url: _rss(_rss_item()))
    films = lb._fetch_watched_rss("user1")
    assert films == [{"slug": "foo", "title": "Foo", "year": 2026, "tmdb_id": 123}]


def test_fetch_watched_rss_handles_review_subpath(monkeypatch):
    # Rewatch links look like .../film/magnolia/1/ — slug is still 'magnolia'.
    monkeypatch.setattr(lb, "_fetch_page",
                        lambda url: _rss(
                            "<item>"
                            "<link>https://letterboxd.com/u/film/magnolia/1/</link>"
                            "<letterboxd:filmTitle xmlns:letterboxd='https://letterboxd.com'>Magnolia</letterboxd:filmTitle>"
                            "<letterboxd:filmYear xmlns:letterboxd='https://letterboxd.com'>1999</letterboxd:filmYear>"
                            "<tmdb:movieId xmlns:tmdb='https://themoviedb.org'>334</tmdb:movieId>"
                            "</item>"))
    films = lb._fetch_watched_rss("user1")
    assert films[0]["slug"] == "magnolia"
    assert films[0]["tmdb_id"] == 334


def test_fetch_watched_rss_missing_tmdb_id_is_none(monkeypatch):
    item = (
        "<item>"
        "<link>https://letterboxd.com/u/film/foo/</link>"
        "<letterboxd:filmTitle xmlns:letterboxd='https://letterboxd.com'>Foo</letterboxd:filmTitle>"
        "<letterboxd:filmYear xmlns:letterboxd='https://letterboxd.com'>2026</letterboxd:filmYear>"
        "</item>"
    )
    monkeypatch.setattr(lb, "_fetch_page", lambda url: _rss(item))
    assert lb._fetch_watched_rss("u")[0]["tmdb_id"] is None


def test_fetch_watched_rss_skips_titleless_items(monkeypatch):
    monkeypatch.setattr(lb, "_fetch_page", lambda url: _rss("<item><link>x</link></item>"))
    assert lb._fetch_watched_rss("u") == []


# ---------------------------------------------------------------------------
# _merge_watched
# ---------------------------------------------------------------------------

def test_merge_watched_dedupes_by_tmdb_id():
    existing = [{"slug": "old", "title": "X", "year": 2024, "tmdb_id": 7}]
    fresh    = [{"slug": "new", "title": "X (rewatch)", "year": 2024, "tmdb_id": 7}]
    merged = lb._merge_watched(existing, fresh)
    assert len(merged) == 1
    assert merged[0]["slug"] == "new"   # fresh wins

def test_merge_watched_falls_back_to_slug_when_no_tmdb_id():
    existing = [{"slug": "foo", "title": "Foo", "year": 2026, "tmdb_id": None}]
    fresh    = [{"slug": "foo", "title": "Foo updated", "year": 2026, "tmdb_id": None}]
    assert len(lb._merge_watched(existing, fresh)) == 1

def test_merge_watched_keeps_old_entries():
    existing = [{"slug": "old", "title": "Old", "year": 2020, "tmdb_id": 1}]
    fresh    = [{"slug": "new", "title": "New", "year": 2026, "tmdb_id": 2}]
    merged = lb._merge_watched(existing, fresh)
    ids = {f["tmdb_id"] for f in merged}
    assert ids == {1, 2}


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
# fetch_watched — RSS + cache merge
# ---------------------------------------------------------------------------

def test_fetch_watched_fresh_cache_skips_network(tmp_path, monkeypatch):
    cache_file = _patch_lb_cache(monkeypatch, tmp_path)
    cache_file.write_text(json.dumps({
        "user1:watched": {"cached_at": time.time(),
                          "films": [{"slug": "w", "title": "W", "year": 2024, "tmdb_id": 9}]}
    }))
    def boom(url): raise AssertionError("unexpected network call")
    monkeypatch.setattr(lb, "_fetch_page", boom)
    assert lb.fetch_watched("user1")[0]["tmdb_id"] == 9


def test_fetch_watched_stale_cache_merges_rss(tmp_path, monkeypatch):
    cache_file = _patch_lb_cache(monkeypatch, tmp_path)
    cache_file.write_text(json.dumps({
        "user1:watched": {"cached_at": 0.0,
                          "films": [{"slug": "old", "title": "Old", "year": 2020, "tmdb_id": 1}]}
    }))
    monkeypatch.setattr(lb, "_fetch_page",
                        lambda url: _rss(_rss_item(title="New", year="2026", tmdb_id="2", slug="new")))
    films = lb.fetch_watched("user1")
    ids = {f["tmdb_id"] for f in films}
    assert ids == {1, 2}   # old kept, new added


def test_fetch_watched_force_bypasses_fresh_cache(tmp_path, monkeypatch):
    cache_file = _patch_lb_cache(monkeypatch, tmp_path)
    cache_file.write_text(json.dumps({
        "user1:watched": {"cached_at": time.time(),
                          "films": [{"slug": "old", "title": "Old", "year": 2020, "tmdb_id": 1}]}
    }))
    fetched = []
    monkeypatch.setattr(lb, "_fetch_page",
                        lambda url: fetched.append(url) or _rss(_rss_item(tmdb_id="2", slug="new", title="New")))
    lb.fetch_watched("user1", force=True)
    assert fetched   # network was hit despite fresh cache
