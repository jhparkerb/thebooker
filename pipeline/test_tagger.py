"""Unit tests for tagger helpers and build_tag_sets — no I/O."""

import pipeline.tagger as tagger
from pipeline.tagger import _should_auto_skip


def _result(tmdb_id=1, genres=None, lang="en", keywords=None):
    return {
        "tmdb_id": tmdb_id,
        "genres": genres or [],
        "original_language": lang,
        "keywords": keywords or [],
    }


# --- genre rules ---

def test_skip_matching_genre():
    assert _should_auto_skip(_result(genres=[10402]), {"genres": [10402]}, set())

def test_no_skip_non_matching_genre():
    assert not _should_auto_skip(_result(genres=[28]), {"genres": [10402]}, set())

def test_watchlist_overrides_genre_skip():
    result = _result(tmdb_id=5, genres=[10402])
    assert not _should_auto_skip(result, {"genres": [10402]}, {5})


# --- language rules ---

def test_skip_matching_language():
    assert _should_auto_skip(_result(lang="hi"), {"skip_languages": ["hi"]}, set())

def test_no_skip_non_matching_language():
    assert not _should_auto_skip(_result(lang="fr"), {"skip_languages": ["hi"]}, set())

def test_watchlist_overrides_language_skip():
    result = _result(tmdb_id=7, lang="hi")
    assert not _should_auto_skip(result, {"skip_languages": ["hi"]}, {7})


# --- keyword rules ---

def test_skip_exact_keyword_match():
    assert _should_auto_skip(
        _result(keywords=["christian"]),
        {"skip_keywords": ["christian"]},
        set()
    )

def test_skip_keyword_substring_match():
    # rule "christian" matches film keyword "christianity"
    assert _should_auto_skip(
        _result(keywords=["christianity"]),
        {"skip_keywords": ["christian"]},
        set()
    )

def test_skip_keyword_case_insensitive_rule():
    # rule keywords are lowercased before comparison
    assert _should_auto_skip(
        _result(keywords=["christianity"]),
        {"skip_keywords": ["CHRISTIAN"]},
        set()
    )

def test_no_skip_unrelated_keyword():
    assert not _should_auto_skip(
        _result(keywords=["action", "thriller"]),
        {"skip_keywords": ["christian"]},
        set()
    )

def test_watchlist_overrides_keyword_skip():
    result = _result(tmdb_id=3, keywords=["gospel"])
    assert not _should_auto_skip(result, {"skip_keywords": ["gospel"]}, {3})


# --- empty rules ---

def test_no_skip_with_empty_rules():
    assert not _should_auto_skip(
        _result(genres=[99], lang="hi", keywords=["christian"]),
        {},
        set()
    )


# ---------------------------------------------------------------------------
# _load_overrides
# ---------------------------------------------------------------------------

def test_load_overrides_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(tagger, "OVERRIDES_PATH", tmp_path / "missing.yaml")
    assert tagger._load_overrides() == {}

def test_load_overrides_parses_yaml(tmp_path, monkeypatch):
    path = tmp_path / "overrides.yaml"
    path.write_text("force_skip_tmdb_ids: [1, 2]\n")
    monkeypatch.setattr(tagger, "OVERRIDES_PATH", path)
    assert tagger._load_overrides() == {"force_skip_tmdb_ids": [1, 2]}


# ---------------------------------------------------------------------------
# _resolve_lb_to_tmdb
# ---------------------------------------------------------------------------

def _tmdb_result(tmdb_id=1, **kw):
    return {"tmdb_id": tmdb_id, "canonical_title": "Film", "year": 2026,
            "genres": [], "original_language": "en", "keywords": [],
            "is_horror": False, **kw}

def test_resolve_lb_to_tmdb_basic(monkeypatch):
    r = _tmdb_result(tmdb_id=42)
    monkeypatch.setattr(tagger, "tmdb_lookup", lambda title, year, token, ttl: r)
    result = tagger._resolve_lb_to_tmdb([{"title": "Foo", "year": 2026}], "tok", 30)
    assert result == {42: r}

def test_resolve_lb_to_tmdb_none_skipped(monkeypatch):
    monkeypatch.setattr(tagger, "tmdb_lookup", lambda *a, **kw: None)
    result = tagger._resolve_lb_to_tmdb([{"title": "Foo", "year": 2026}], "tok", 30)
    assert result == {}


# ---------------------------------------------------------------------------
# build_tag_sets
# ---------------------------------------------------------------------------

_CFG = {
    "tmdb": {"read_access_token": "tok", "cache_ttl_days": 30},
    "letterboxd": {"username": "user1"},
}

def _setup(monkeypatch, *, watchlist=None, watched=None, overrides=None, lookup_map=None):
    monkeypatch.setattr(tagger, "fetch_watchlist", lambda user: watchlist or [])
    monkeypatch.setattr(tagger, "fetch_watched",   lambda user: watched   or [])
    monkeypatch.setattr(tagger, "_load_overrides", lambda: overrides or {})
    lm = lookup_map or {}
    monkeypatch.setattr(tagger, "tmdb_lookup",
                        lambda title, year, token, ttl: lm.get(title))

def test_build_tag_sets_must_see_from_watchlist(monkeypatch):
    r = _tmdb_result(tmdb_id=10)
    _setup(monkeypatch, watchlist=[{"title": "Foo", "year": 2026}], lookup_map={"Foo": r})
    tags = tagger.build_tag_sets(_CFG, [("Foo", 2026)])
    assert 10 in tags.must_see
    assert 10 not in tags.skip

def test_build_tag_sets_skip_watched(monkeypatch):
    r = _tmdb_result(tmdb_id=20)
    _setup(monkeypatch, watched=[{"title": "Foo", "year": 2026}], lookup_map={"Foo": r})
    tags = tagger.build_tag_sets(_CFG, [("Foo", 2026)])
    assert 20 in tags.skip
    assert 20 not in tags.must_see

def test_build_tag_sets_watchlist_overrides_watched(monkeypatch):
    r = _tmdb_result(tmdb_id=30)
    _setup(monkeypatch,
           watchlist=[{"title": "Foo", "year": 2026}],
           watched=[{"title": "Foo", "year": 2026}],
           lookup_map={"Foo": r})
    tags = tagger.build_tag_sets(_CFG, [("Foo", 2026)])
    assert 30 in tags.must_see
    assert 30 not in tags.skip

def test_build_tag_sets_force_skip(monkeypatch):
    r = _tmdb_result(tmdb_id=40)
    _setup(monkeypatch, overrides={"force_skip_tmdb_ids": [40]}, lookup_map={"Foo": r})
    tags = tagger.build_tag_sets(_CFG, [("Foo", 2026)])
    assert 40 in tags.skip
    assert 40 not in tags.must_see

def test_build_tag_sets_horror(monkeypatch):
    r = _tmdb_result(tmdb_id=50, genres=[27], is_horror=True)
    _setup(monkeypatch, lookup_map={"Foo": r})
    tags = tagger.build_tag_sets(_CFG, [("Foo", 2026)])
    assert 50 in tags.horror

def test_build_tag_sets_tmdb_none_silently_skipped(monkeypatch):
    _setup(monkeypatch, lookup_map={"Foo": None})
    tags = tagger.build_tag_sets(_CFG, [("Foo", 2026)])
    assert not tags.must_see and not tags.skip and not tags.horror

def test_build_tag_sets_auto_skip_genre(monkeypatch):
    r = _tmdb_result(tmdb_id=60, genres=[10402])
    _setup(monkeypatch, overrides={"auto_skip": {"genres": [10402]}}, lookup_map={"Foo": r})
    tags = tagger.build_tag_sets(_CFG, [("Foo", 2026)])
    assert 60 in tags.skip

def test_build_tag_sets_empty_showings(monkeypatch):
    _setup(monkeypatch)
    tags = tagger.build_tag_sets(_CFG, [])
    assert not tags.must_see and not tags.skip and not tags.horror
