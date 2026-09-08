# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

News scraper focused on retail, supermarkets, mass consumption, commercial logistics, and corporate signals in Chile. It aggregates news from 25 sources, scores each article for relevance, stores in PostgreSQL, and delivers summaries via WhatsApp through Evolution API.

## Commands

All commands require the `.venv` virtual environment and `PYTHONPATH=src`.

```bash
# Activate venv
source .venv/bin/activate

# Full pipeline (scrape → score → save → WhatsApp delivery)
inv run-news                      # todas las fuentes
inv run-news --grupo frecuentes   # solo las que corren cada 3 h
inv run-news --grupo diarios      # solo las salas de prensa corporativas
# or directly:
PYTHONPATH=src SCRAPER_GRUPO=todos ./.venv/bin/python src/main.py

# Unit tests (pytest, no DB, no network)
inv test

# Test all scrapers (validates output without saving to DB — hits live sites)
inv test-scrapers

# Test a specific scraper
inv test-scrapers --source walmartchile
inv list-sources  # shows valid source names

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
4. Fetch page metadata concurrently (`extraer_metadatos_batch`, concurrency=8) for new
   candidates only: excerpt **and** `og:image`, from a single visit per URL
5. Score each candidate with `score_noticia(title, url, source, excerpt)`; discard if `score < SCORE_MINIMO` (currently 3)
6. Resolve the cover image: `noticia.img` if the scraper found one, else the `og:image`
   from step 4. **An article with neither is dropped** — `noticia.img` is NOT NULL
7. Save passing articles as `Noticia` rows; catch `IntegrityError` for late duplicates
8. Update `ScrapeRunSource` stats per source
9. Call `enviar_noticias_pendientes` to deliver unseen news to active WhatsApp users

### Scraper contract (`src/scrapers/base.py`)

Each scraper extends `BaseScraper`, sets a `source: str` class attribute, and implements `fetch() -> list[NoticiaSchema]`. The schema (`src/schemas.py`) requires `title`, `url`, `date_preview` and `source`; `img` y `excerpt` son opcionales porque el pipeline los completa desde la nota (`og:image` / `og:description`).

**Si la fuente publica RSS, extiende `RSSScraper` (`src/scrapers/rss.py`) y no
`BaseScraper`**: ya resuelve fecha RFC 822, imagen (media:content, enclosure o el
`<img>` del `content:encoded`), dedup por URL y la basura que Cloudflare pega
después de `</rss>`. Un scraper de RSS nuevo son cinco líneas — ver
`peruretail.py`. `gestion.py` es anterior y mantiene su implementación propia.

`BaseScraper` ya provee lo que antes estaba copiado en cada archivo — **no volver a duplicarlo**:

- `HEADERS`: User-Agent + `Accept-Language`. Se usa como `self.HEADERS`.
- `_clean_text(value)`: desescapa entidades, quita tags, colapsa espacios.
- `_absolute_url(value)`: resuelve rutas relativas contra `BASE_URL`. **Si un
  scraper llama a `_absolute_url`, debe declarar `BASE_URL`** (hay un test que
  lo verifica en `tests/test_base_scraper.py`).

`DFLabScraper` exists in `src/scrapers/dflab.py` and is exported from `__init__.py`, but is intentionally excluded from `config.SCRAPERS` — do not add it back without testing.

### Grupos de fuentes y cadencia (`src/config.py`)

- `SCRAPERS_FRECUENTES` (21): medios y portales que publican todo el día. Cron cada 3 h.
- `SCRAPERS_DIARIOS` (4): salas de prensa corporativas (walmart, cencosud, smu,
  capital). Publican 1-2 veces al mes; revisarlas cada 3 h era trabajo perdido
  (smu: 3.760 revisadas → 3 noticias en 30 días). Cron una vez al día.
- `SCRAPERS` es la unión y sigue siendo el catálogo completo para
  `inv list-sources` y `test_scrapers.py`.

El grupo se elige con `SCRAPER_GRUPO` (`frecuentes` | `diarios` | `todos`).

`_run_scraper` reintenta cada fuente hasta `SCRAPER_MAX_INTENTOS` (3) con
backoff lineal de `SCRAPER_BACKOFF_SEGUNDOS` (5 s): la mayoría de las fallas son
timeouts transitorios de Playwright, no errores de parseo.

### Scoring (`src/utils/scorer.py`)

Pure keyword-matching scorer, no ML. Works on normalized (lowercased, accent-stripped) title + excerpt. Layers:
- **HIGH_IMPACT** (×4): specific retail brands (Walmart, Jumbo, Cencosud, etc.)
- **TOPIC_WORDS** (×3): generic retail/commerce terms
- **SUPPLIER_WORDS** (×2): CPG/FMCG brands (Coca-Cola, Nestlé, etc.)
- **INDIRECT_WORDS** (×1, only with retail signal): logistics, financial results, openings, etc.
- Bonuses for combinations; penalties for crime, politics, generic international news
- `source`/`url` only add +1 and only when a retail signal already exists in the text

To tune the scorer, edit the keyword lists in `src/utils/scorer_keywords.py` and validate with `inv test` (`tests/test_scorer.py`). Los tests afirman sobre el *contrato* — si una noticia relevante pasa `SCORE_MINIMO` y una de ruido no — y no sobre el número exacto, para que afinar el scorer no los rompa sin motivo.

### Database (`src/database.py`)

SQLAlchemy 2.0 (`DeclarativeBase`) with PostgreSQL, engines sync (`psycopg2`) y async (`asyncpg`), ambos con `pool_pre_ping`. **Las migraciones son Alembic** (`alembic/versions/`): `create_db()` ejecuta `alembic upgrade head`. En la API no corre en el `lifespan` sino como `ExecStartPre` del service (ver `docs/auditoria/`), para que 2 workers no migren en paralelo.

`sqlmodel` sigue en `requirements.txt` aunque los modelos ya no lo usen: la migración inicial `aaf1d98822c0` importa `sqlmodel.sql.sqltypes` y sin él un `upgrade head` desde cero falla.

Key tables: `noticia` (unique on `url`), `usuario`, `usuarionoticiavista` (FK to noticia uses `ON DELETE CASCADE`), `scraperun`, `scraperunsource`.

### Delivery (`src/services/news_delivery.py`)

Sends up to `MAX_NOTICIAS_POR_ENVIO` (20) unseen articles per active user. Articles older
than 4 days (`MAX_NEWS_AGE_DAYS`) are auto-marked as `omitida_antigua` without sending.
Uses `BotWhatsApp` (`src/utils/whatsapp.py`) which wraps Evolution API.

**El envío se parte en varios mensajes.** WhatsApp trunca un texto en 4.096
caracteres y cada noticia pesa ~450, así que 20 son ~8.200: `construir_mensajes`
corta en bloques de `MAX_CARACTERES_MENSAJE` (3.500) numerados de corrido y
rotulados `(n/total)`. Cada parte viaja con las noticias que contiene y se
registran como enviadas **por parte**: si la tercera falla, las dos primeras
quedan marcadas y el resto vuelve a estar pendiente en la corrida siguiente,
en vez de darse por visto algo que nunca salió.

### Excerpt and image extraction (`src/utils/excerpt.py`)

Async `httpx` fetcher (concurrency-limited via `asyncio.Semaphore`). `extraer_metadatos_batch`
devuelve un `MetadatosPagina(excerpt, img)` por URL, de **una sola visita**.

- Bajada: `og:description` → `description` → JSON-LD → primer `<p>` largo. Corta en 500 chars.
- Imagen: `og:image` → `twitter:image`, resuelta a absoluta contra la URL final
  (post-redirect). Existe porque los feeds de Perú Retail, Expansión y EjePrime no
  traen imagen y sin esto esas fuentes no guardarían nada.

`extraer_bajadas_batch` sigue existiendo como proyección para los scripts de
auditoría y backfill, a los que la imagen no les sirve.

## Environment variables

See `.env.example`. Required: `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_NAME`. Optional: `DATABASE_HOST` (default `127.0.0.1`), `DATABASE_PORT` (default `5432`), Evolution API vars (`URL_EVOLUTION`, `INSTANCE_EVOLUTION`, `APIKEY_EVOLUTION`).

## Adding a new scraper

1. Create `src/scrapers/<name>.py`. **Si el medio tiene RSS, extiende `RSSScraper`**
   y declara solo `source`, `country`, `BASE_URL` y `URL`. Si no, extiende `BaseScraper`.
   Usa `self.HEADERS`, `self._clean_text()` y `self._absolute_url()` de la base;
   si llamas a `_absolute_url`, declara `BASE_URL`.
2. Export from `src/scrapers/__init__.py`
3. Add the class to **`SCRAPERS_FRECUENTES`** (medio que publica a diario) o
   **`SCRAPERS_DIARIOS`** (sala de prensa corporativa) en `src/config.py`
4. Validate with `inv test-scrapers --source <source-name>` y `inv test`

## Production environment

This repository runs in production. The API is served via `gunicorn` with uvicorn workers (`noticias-api.service`, 2 workers, puerto 8001) behind Nginx as a reverse proxy. **After any API code change, restart only the uvicorn service — Nginx does not need to be touched.**

```bash
# Restart the API after code changes
sudo systemctl restart noticias-api

# Check status / logs
sudo systemctl status noticias-api
journalctl -u noticias-api -f
```

The scraper pipeline runs on a cron schedule. Changes to `src/main.py` or scrapers take effect on the next cron trigger — no restart needed for those.
