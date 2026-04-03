import logging
import os
from datetime import datetime
from pathlib import Path

from sqlalchemy.exc import IntegrityError
from sqlmodel import select

import config as ENV
from database import create_db, get_session
from models import Noticia, ScrapeRun, ScrapeRunSource
from services.news_delivery import enviar_noticias_pendientes
from utils import extraer_bajadas_batch, score_noticia, setup_logging


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_LOG_FILE = BASE_DIR / "logs" / "news_scraper.log"
LOGGER = logging.getLogger("news_scraper")


def procesar_noticias(trigger: str = "manual") -> dict[str, object]:
    session = next(get_session())
    total_nuevas = 0
    total_revisadas = 0
    errores: list[dict[str, str]] = []

    scrape_run = ScrapeRun(
        trigger=trigger,
        total_sources=len(ENV.SCRAPERS),
        status="running",
    )
    session.add(scrape_run)
    session.commit()
    session.refresh(scrape_run)

    LOGGER.info("Iniciando proceso de scraping con %s fuentes", len(ENV.SCRAPERS))

    for ScraperClass in ENV.SCRAPERS:
        scraper = ScraperClass()
        LOGGER.info("Scrapeando fuente=%s", scraper.source)
        reviewed_count = 0
        nuevas_fuente = 0
        error_count = 0
        source_status = "ok"
        error_message = None

        try:
            noticias = scraper.fetch()
        except Exception as e:
            LOGGER.exception("Error en fuente=%s", scraper.source)
            errores.append({"source": scraper.source, "error": str(e)})
            source_status = "error"
            error_count = 1
            error_message = str(e)
            noticias = []

        if source_status == "ok":
            seen_urls_batch: set[str] = set()
            candidatas = []

            for noticia in noticias:
                total_revisadas += 1
                reviewed_count += 1

                if noticia.url in seen_urls_batch:
                    LOGGER.debug("Noticia duplicada en lote omitida url=%s", noticia.url)
                    continue

                existing = session.exec(select(Noticia.id).where(Noticia.url == noticia.url)).first()
                if existing is not None:
                    LOGGER.debug("Noticia ya existe en BD, omitida url=%s", noticia.url)
                    continue

                seen_urls_batch.add(noticia.url)
                candidatas.append(noticia)

            excerpt_map = extraer_bajadas_batch(
                [noticia.url for noticia in candidatas],
                concurrency=4,
            ) if candidatas else {}

            for noticia in candidatas:
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
                    excerpt=excerpt,
                    score=score,
                )

                try:
                    session.add(db_noticia)
                    session.commit()
                    session.refresh(db_noticia)
                    seen_urls_batch.add(noticia.url)
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
                    continue

        source_row = ScrapeRunSource(
            scrape_run_id=scrape_run.id,
            source=scraper.source,
            reviewed_count=reviewed_count,
            new_count=nuevas_fuente,
            error_count=error_count,
            status=source_status,
            error_message=error_message,
        )
        session.add(source_row)
        session.commit()

        LOGGER.info(
            "Fuente procesada fuente=%s revisadas=%s nuevas=%s",
            scraper.source,
            reviewed_count,
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
