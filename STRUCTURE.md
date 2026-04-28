# Codebase Structure

## Overview

The Booker is a weekend movie scheduling tool. It scrapes showtimes from theater APIs, enriches them with TMDB genre data and Letterboxd watchlist/watched data, then runs a branch-and-bound optimizer to find the best schedule of films to see in a single day (or weekend).

## Data flow

```
config.yaml / overrides.yaml
        │
        ▼
  pipeline.py (entry point)
        │
        ├─► scrapers/amc.py ──► AMC API ──► [Showing, ...]
        │
        ├─► tagger.py ──► letterboxd.py ──► Letterboxd HTML/CSV
        │              └─► tmdb.py      ──► TMDB API
        │              └─► [TagSets]
        │
        ├─► optimizer.py ──► [schedule, ...]   (ranked by score)
        │
        └─► digest.py ──► stdout
```

## Package: `pipeline/`

### `optimizer.py`
Core data model and scheduling algorithm.

- **`Showing`** — frozen dataclass: title, theater, day, start time, runtime, format, recliner flag, TMDB id
- **`ScoringConfig`** — scoring weights (base per film, must-see bonus, horror bonus, format bonuses, recliner bonus, diversity bonus); overridable via `config.yaml`
- **`TagSets`** — three sets (`must_see`, `horror`, `skip`), matched by TMDB id with fallback to canonical title
- **`score_showing()`** — per-film score given tags and config
- **`solve()`** — branch-and-bound DFS; returns top-k non-overlapping schedules ranked by `weekend_score`
- **`weekend_score()`** — aggregate score across a set of schedules (accounts for coverage across both days)
- **`tier_label()`** — maps score to a qualitative tier string

### `tagger.py`
Builds `TagSets` for the titles currently playing.

- Fetches user's Letterboxd watchlist → `must_see` candidates
- Fetches user's Letterboxd watched list → `skip` candidates
- Resolves both lists to TMDB ids via `tmdb.lookup`
- Looks up each currently-playing title on TMDB for genre/language/keyword data
- Applies `overrides.yaml` rules: `force_skip_tmdb_ids`, `auto_skip` (genre, language, keywords)
- Watchlist membership always overrides watched/auto-skip

### `tmdb.py`
TMDB API client with local JSON cache.

- **`lookup(title, year, token, ttl_days)`** — searches TMDB, fetches keywords, returns `{tmdb_id, canonical_title, year, is_horror, genres, original_language, keywords}` or `None`
- Cache stored at `pipeline/cache/tmdb.json`; TTL defaults to 180 days (TMDB ToS maximum)
- Retries up to 3× on HTTP 429 with exponential backoff

### `letterboxd.py`
Letterboxd data access — watchlist and watched list.

- **`fetch_watchlist(username)`** — scrapes HTML poster grid; paginates; stops early once no recent films remain (configurable `min_year`)
- **`fetch_watched(username, csv_path=None)`** — prefers a CSV export (`watched.csv` from LB Settings → Data → Export); falls back to HTML scraping
- Cache stored at `pipeline/cache/letterboxd.json`; watchlist TTL 7 days, watched TTL 30 days
- Uses `urllib` (stdlib); 2s delay between pages

### `digest.py`
Renders the final schedule to stdout.

- **`render(results, tags, days, cfg)`** — top-level; iterates theaters and days, prints schedule blocks
- Per-schedule header: must-see count, horror count, total films, score
- Per-film line: time range, title, format tags, `(depart)` annotation for non-final films
- Warns about must-sees that didn't appear in any viable schedule

### `pipeline.py`
Entry point — wires everything together.

- **`run(cfg, days)`** — fetches showings for each theater, resolves tags, runs optimizer, renders digest
- **`main()`** — CLI: `--date YYYY-MM-DD` (defaults to today); computes the containing weekend
- Skips theaters with unsupported chains (warns to stderr); swallows per-day scrape errors

### `scrapers/`

- **`base.py`** — `Scraper` ABC with one method: `fetch(theater_id, day) → [Showing]`
- **`amc.py`** — AMC catalog API scraper
  - Caches raw JSON responses per `(theater_id, date)` under `pipeline/cache/amc/`
  - Parses format codes (IMAX, DOLBY, PRIME, PLF→IMAX, 3D) and recliner codes
  - `find_theater_id(search_text)` — helper for one-time theater ID lookup
  - Retries up to 3× on HTTP 429

## Configuration

### `config.yaml`
Runtime configuration (not committed; see `config.example.yaml`):
```yaml
tmdb:
  read_access_token: "..."
  cache_ttl_days: 180

letterboxd:
  username: "..."

amc:
  vendor_key: "..."

theaters:
  - id: my-amc
    chain: amc
    chain_id: "1234"
    name: "AMC Waterfront 22"

scoring:                    # all optional — these are the defaults
  base_per_film: 100.0
  must_see_bonus: 50.0
  horror_bonus: 30.0
```

### `overrides.yaml`
Manual curation rules:
```yaml
force_skip_tmdb_ids: [12345]          # always skip regardless of watchlist

auto_skip:
  genres: [10402]                     # TMDB genre ids
  skip_languages: [hi, ta]
  skip_keywords: [christian, gospel]
```

## Scripts (`scripts/`)

Code quality metrics, run via `make quality`:

| Target | Script | What it measures |
|---|---|---|
| `make loc` | — | Lines of code per file |
| `make complexity` | `complexity.py` | Cyclomatic complexity (AST) |
| `make funclength` | `funclength.py` | Function line counts |
| `make annotations` | `annotations.py` | Type annotation coverage |
| `make coverage` | pytest-cov | Test coverage |
| `make quality` | all of the above | Combined report |

## Tests

All tests live alongside the modules they test (`test_*.py`). No network calls — all external I/O is monkeypatched. Current coverage: **97%**.

| Test file | Covers |
|---|---|
| `test_optimizer.py` | `optimizer.py` — scheduling, scoring, tagging |
| `test_digest.py` | `digest.py` — formatting helpers, render integration |
| `test_pipeline.py` | `pipeline.py` — `_weekend_days`, `_scoring_cfg`, `_make_scraper` |
| `test_pipeline_run.py` | `pipeline.py` — `run()`, `main()` |
| `test_tagger.py` | `tagger.py` — `_should_auto_skip`, `build_tag_sets` |
| `test_tmdb.py` | `tmdb.py` — cache, lookup logic, retry behavior |
| `test_letterboxd.py` | `letterboxd.py` — parser, pagination, CSV, cache |
| `scrapers/test_amc.py` | `scrapers/amc.py` — parsing helpers, cache, scraper, retry |
