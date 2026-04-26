"""Unit tests for tagger._should_auto_skip — pure function, no I/O."""

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
