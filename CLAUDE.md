# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

News scraper focused on retail, supermarkets, mass consumption, commercial logistics, and corporate signals in Chile. It aggregates news from ~17 sources, scores each article for relevance, stores in PostgreSQL, and delivers summaries via WhatsApp through Evolution API.

## Commands

All commands require the `.venv` virtual environment and `PYTHONPATH=src`.

```bash
# Activate venv
source .venv/bin/activate

# Full pipeline (scrape → score → save → WhatsApp delivery)
inv run-news
# or directly:
PYTHONPATH=src ./.venv/bin/python src/main.py

# Test all scrapers (validates output without saving to DB)
inv test-scrapers

# Test a specific scraper
inv test-scrapers --source walmartchile
inv list-sources  # shows valid source names

# Run scorer test cases (no DB needed)
PYTHONPATH=src ./.venv/bin/python src/scripts/test_scorer_cases.py

# Generate and send review CSV via WhatsApp
inv review-csv
# or without sending:
PYTHONPATH=src ./.venv/bin/python src/scripts/export_scrape_review_csv.py --no-send

# Start PostgreSQL via Docker
docker compose -f compose.yaml up -d

# Tail logs
tail -f logs/news_scraper.log
tail -f logs/cron.log
```

## Architecture

### Pipeline flow (`src/main.py: procesar_noticias`)

1. Create a `ScrapeRun` record in DB (for traceability)
2. For each scraper in `config.SCRAPERS`: call `scraper.fetch()` → returns `list[NoticiaSchema]`
3. Deduplicate within the batch and against existing DB URLs
4. Fetch excerpts concurrently (`extraer_bajadas_batch`, concurrency=4) for new candidates only
5. Score each candidate with `score_noticia(title, url, source, excerpt)`; discard if `score < SCORE_MINIMO` (currently 3)
6. Save passing articles as `Noticia` rows; catch `IntegrityError` for late duplicates
7. Update `ScrapeRunSource` stats per source
8. Call `enviar_noticias_pendientes` to deliver unseen news to active WhatsApp users

### Scraper contract (`src/scrapers/base.py`)

Each scraper extends `BaseScraper`, sets a `source: str` class attribute, and implements `fetch() -> list[NoticiaSchema]`. The schema (`src/schemas.py`) requires `title`, `url`, `img`, `date_preview`, `source`, and optional `excerpt`.

`DFLabScraper` exists in `src/scrapers/dflab.py` and is exported from `__init__.py`, but is intentionally excluded from `config.SCRAPERS` — do not add it back without testing.

### Scoring (`src/utils/scorer.py`)

Pure keyword-matching scorer, no ML. Works on normalized (lowercased, accent-stripped) title + excerpt. Layers:
- **HIGH_IMPACT** (×4): specific retail brands (Walmart, Jumbo, Cencosud, etc.)
- **TOPIC_WORDS** (×3): generic retail/commerce terms
- **SUPPLIER_WORDS** (×2): CPG/FMCG brands (Coca-Cola, Nestlé, etc.)
- **INDIRECT_WORDS** (×1, only with retail signal): logistics, financial results, openings, etc.
- Bonuses for combinations; penalties for crime, politics, generic international news
- `source`/`url` only add +1 and only when a retail signal already exists in the text

To tune the scorer, edit the keyword lists at the top of `scorer.py` and validate with `test_scorer_cases.py`.

### Database (`src/database.py`)

SQLModel/SQLAlchemy with PostgreSQL. No migration framework — schema changes are applied inline via `_run_schema_updates()` which runs `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` idempotently. Call `create_db()` once before using the DB (done automatically in `main.py`).

Key tables: `noticia` (unique on `url`), `usuario`, `usuarionoticiavista` (FK to noticia uses `ON DELETE CASCADE`), `scraperun`, `scraperunsource`.

### Delivery (`src/services/news_delivery.py`)

Sends up to 10 unseen articles per active user. Articles older than 4 days (`MAX_NEWS_AGE_DAYS`) are auto-marked as `omitida_antigua` without sending. Uses `BotWhatsApp` (`src/utils/whatsapp.py`) which wraps Evolution API.

### Excerpt extraction (`src/utils/excerpt.py`)

Async `httpx` fetcher (concurrency-limited via `asyncio.Semaphore`). Tries in order: `og:description` meta tag → `description` meta tag → JSON-LD fields → first long `<p>` tag. Truncates at 500 chars.

## Environment variables

See `.env.example`. Required: `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_NAME`. Optional: `DATABASE_HOST` (default `127.0.0.1`), `DATABASE_PORT` (default `5432`), Evolution API vars (`URL_EVOLUTION`, `INSTANCE_EVOLUTION`, `APIKEY_EVOLUTION`).

## Adding a new scraper

1. Create `src/scrapers/<name>.py` extending `BaseScraper` with a unique `source` string
2. Export from `src/scrapers/__init__.py`
3. Add the class to `SCRAPERS` list in `src/config.py`
4. Validate with `inv test-scrapers --source <source-name>`
