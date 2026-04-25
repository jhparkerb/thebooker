# The Booker

Weekend movie schedule optimizer for Pittsburgh-area theaters. Scrapes showtimes,
cross-references your Letterboxd watchlist and watched history, and emits a ranked
digest of the best possible film marathon at each theater.

## Setup

**1. Dependencies**

```
pip install pyyaml rapidfuzz requests
```

**2. Config**

```bash
cp config.example.yaml config.yaml
```

Fill in `config.yaml` with your credentials (this file is gitignored):

- `tmdb.read_access_token` — from [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api) (free)
- `amc.vendor_key` — from [AMC Developer Portal](https://developers.amctheatres.com) (free, deploys Thursdays)
- `letterboxd.username` — your public Letterboxd username
- `theaters[].chain_id` — run `python -m pipeline.scrapers.amc --find` to look up the numeric ID

**3. Overrides (optional)**

`overrides.yaml` controls rule-based filtering:

```yaml
auto_skip:
  genres: [10402]           # TMDB genre IDs to skip (10402 = Music/concert)
  skip_languages: [hi, ta]  # ISO 639-1 language codes
  skip_keywords: [evangelical, faith-based]  # TMDB keyword substrings
force_skip_tmdb_ids: []     # always skip these titles regardless of rules
force_must_see_tmdb_ids: [] # always flag these as must-see
force_horror_tmdb_ids: []   # always flag these as horror
```

## Running

```bash
python -m pipeline.pipeline
```

Digest is written to stdout. Wire to cron/launchd for weekly delivery.

## Architecture

```
pipeline/
  pipeline.py       entrypoint
  optimizer.py      branch-and-bound schedule solver
  tagger.py         builds TagSets (must_see / horror / skip) from LB + TMDB + overrides
  tmdb.py           TMDB title lookup with 180-day cache
  letterboxd.py     watchlist + watched scraper (HTML pagination or CSV export)
  digest.py         cross-theater ranking and stdout formatting
  scrapers/
    base.py         Scraper ABC
    amc.py          AMC catalog API  (python -m pipeline.scrapers.amc --find)
    cinemark.py     (planned)
```

## Scoring tiers

| Score  | Label            |
|--------|------------------|
| ≥ 1200 | marathon-grade   |
| ≥ 900  | solid day        |
| ≥ 600  | decent           |
| < 600  | thin weekend     |

Thresholds are tunable in `config.yaml` under `tiers`. Calibrated against the
Apr 25–26 2026 weekend at AMC Waterfront 22 (optimizer score: ~1451).

## Attribution

This application uses TMDB and the TMDB APIs but is not endorsed, certified,
or otherwise approved by TMDB.

## License

Apache 2.0 — see [LICENSE](LICENSE).
