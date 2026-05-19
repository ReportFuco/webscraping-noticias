import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

import config as ENV
from scrapers.base import BaseScraper
from database import create_db, get_session
from models import Noticia, ScrapeRun, ScrapeRunSource
from schemas import NoticiaSchema
from services.news_delivery import enviar_noticias_pendientes
from utils import extraer_bajadas_batch, score_noticia, setup_logging
from utils.date_formater import parse_date_preview


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_LOG_FILE = BASE_DIR / "logs" / "news_scraper.log"
LOGGER = logging.getLogger("news_scraper")


def _run_scraper(ScraperClass: type[BaseScraper]) -> tuple[str, list[NoticiaSchema], Exception | None]:
    scraper = ScraperClass()
    try:
        noticias = scraper.fetch()
        return scraper.source, noticias, None
    except Exception as e:
        logging.getLogger("news_scraper").exception("Error en fuente=%s", scraper.source)
        return scraper.source, [], e


def procesar_noticias(trigger: str = "manual") -> dict[str, object]:
    session = next(get_session())
    total_nuevas = 0
    errores: list[dict[str, str]] = []

    scrape_run = ScrapeRun(
        trigger=trigger,
        total_sources=len(ENV.SCRAPERS),
        status="running",
    )
    session.add(scrape_run)
    session.commit()
    session.refresh(scrape_run)

    LOGGER.info(
        "Iniciando proceso de scraping con %s fuentes (paralelo, workers=%s)",
        len(ENV.SCRAPERS),
        min(len(ENV.SCRAPERS), ENV.MAX_SCRAPER_WORKERS),
    )

    # Phase 1: run all scrapers concurrently
    raw_results: dict[str, tuple[list[NoticiaSchema], Exception | None]] = {}
    with ThreadPoolExecutor(max_workers=min(len(ENV.SCRAPERS), ENV.MAX_SCRAPER_WORKERS)) as pool:
        futures = {pool.submit(_run_scraper, cls): cls for cls in ENV.SCRAPERS}
        for future in as_completed(futures):
            source, noticias, error = future.result()
            raw_results[source] = (noticias, error)
            if error:
                LOGGER.warning("Scraper falló fuente=%s error=%s", source, error)
            else:
                LOGGER.info("Scraper completado fuente=%s noticias=%s", source, len(noticias))

    # Phase 2: bulk URL deduplication — one query for all candidates
    all_candidate_urls: list[str] = []
    seen_global: set[str] = set()
    for ScraperClass in ENV.SCRAPERS:
        noticias, error = raw_results.get(ScraperClass.source, ([], None))
        if error:
            continue
        for n in noticias:
            if n.url not in seen_global:
                seen_global.add(n.url)
                all_candidate_urls.append(n.url)

    existing_urls: set[str] = set()
    if all_candidate_urls:
        existing_urls = set(
            session.execute(select(Noticia.url).where(Noticia.url.in_(all_candidate_urls))).scalars().all()
        )

    # Phase 3: collect per-source candidates (preserve source order for stats)
    source_candidates: dict[str, list[NoticiaSchema]] = {}
    source_reviewed: dict[str, int] = {}
    deduped: set[str] = set(existing_urls)

    for ScraperClass in ENV.SCRAPERS:
        source = ScraperClass.source
        noticias, error = raw_results.get(source, ([], None))
        if error:
            source_reviewed[source] = 0
            source_candidates[source] = []
            continue

        candidates: list[NoticiaSchema] = []
        for n in noticias:
            if n.url not in deduped:
                deduped.add(n.url)
                candidates.append(n)

        source_reviewed[source] = len(noticias)
        source_candidates[source] = candidates

    total_revisadas = sum(source_reviewed.values())

    # Phase 4: single excerpt batch for all candidates across all sources
    all_candidates = [n for cands in source_candidates.values() for n in cands]
    excerpt_map = (
        extraer_bajadas_batch([n.url for n in all_candidates], concurrency=8)
        if all_candidates
        else {}
    )

    # Phase 5: score, save, and record ScrapeRunSource per source
    for ScraperClass in ENV.SCRAPERS:
        source = ScraperClass.source
        noticias, error = raw_results.get(source, ([], None))

        source_status = "error" if error else "ok"
        error_message = str(error) if error else None
        error_count = 1 if error else 0
        nuevas_fuente = 0

        if error:
            errores.append({"source": source, "error": str(error)})
        else:
            for noticia in source_candidates.get(source, []):
                excerpt = excerpt_map.get(noticia.url) or noticia.excerpt
                score = score_noticia(
                    noticia.title,
                    noticia.url,
                    noticia.source,
                    excerpt or "",
                )

                if score < ENV.SCORE_MINIMO:
                    continue

                db_noticia = Noticia(
                    scrape_run_id=scrape_run.id,
                    title=noticia.title,
                    url=noticia.url,
                    img=noticia.img,
                    date_preview=noticia.date_preview,
                    source=noticia.source,
                    country=noticia.country,
                    excerpt=excerpt,
                    score=score,
                    published_date=parse_date_preview(str(noticia.date_preview)),
                )

                try:
                    session.add(db_noticia)
                    session.commit()
                    session.refresh(db_noticia)
                    LOGGER.info(
                        "Noticia guardada fuente=%s score=%s title=%s",
                        noticia.source,
                        score,
                        noticia.title[:80],
                    )
                    total_nuevas += 1
                    nuevas_fuente += 1
                except IntegrityError:
                    session.rollback()
                    LOGGER.debug("Noticia duplicada omitida url=%s", noticia.url)

        source_row = ScrapeRunSource(
            scrape_run_id=scrape_run.id,
            source=source,
            reviewed_count=source_reviewed.get(source, 0),
            new_count=nuevas_fuente,
            error_count=error_count,
            status=source_status,
            error_message=error_message,
        )
        session.add(source_row)
        session.commit()

        LOGGER.info(
            "Fuente procesada fuente=%s revisadas=%s nuevas=%s",
            source,
            source_reviewed.get(source, 0),
            nuevas_fuente,
        )

    delivery = enviar_noticias_pendientes(session)

    scrape_run.finished_at = datetime.now()
    scrape_run.total_reviewed = total_revisadas
    scrape_run.total_new = total_nuevas
    scrape_run.total_errors = len(errores)
    scrape_run.status = "partial" if errores else "ok"
    session.add(scrape_run)
    session.commit()

    resumen = {
        "scrape_run_id": scrape_run.id,
        "total_revisadas": total_revisadas,
        "total_nuevas": total_nuevas,
        "errores": errores,
        "delivery": delivery,
    }
    LOGGER.info("Proceso finalizado resumen=%s", resumen)
    return resumen


if __name__ == "__main__":
    setup_logging(
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_file=os.getenv("LOG_FILE", str(DEFAULT_LOG_FILE)),
    )
    create_db()
    procesar_noticias(trigger=os.getenv("SCRAPER_TRIGGER", "manual"))
