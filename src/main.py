import logging
import os
from pathlib import Path

from sqlalchemy.exc import IntegrityError

import config as ENV
from database import create_db, get_session
from models import Noticia
from utils import extraer_bajada, score_noticia, setup_logging


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_LOG_FILE = BASE_DIR / "logs" / "news_scraper.log"
LOGGER = logging.getLogger("news_scraper")


def procesar_noticias() -> dict[str, str]:
    session = next(get_session())
    total_nuevas = 0
    total_revisadas = 0
    errores: list[dict[str, str]] = []

    LOGGER.info("Iniciando proceso de scraping con %s fuentes", len(ENV.SCRAPERS))

    for ScraperClass in ENV.SCRAPERS:
        scraper = ScraperClass()
        LOGGER.info("Scrapeando fuente=%s", scraper.source)

        try:
            noticias = scraper.fetch()
        except Exception as e:
            LOGGER.exception("Error en fuente=%s", scraper.source)
            errores.append({"source": scraper.source, "error": str(e)})
            continue

        nuevas_fuente = 0

        for noticia in noticias:
            total_revisadas += 1

            excerpt = extraer_bajada(noticia.url) or noticia.excerpt
            score = score_noticia(
                noticia.title,
                noticia.url,
                noticia.source,
                excerpt or "",
            )

            if score < ENV.SCORE_MINIMO:
                continue

            db_noticia = Noticia(
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

        LOGGER.info(
            "Fuente procesada fuente=%s revisadas=%s nuevas=%s",
            scraper.source,
            len(noticias),
            nuevas_fuente,
        )

    resumen = {
        "total_revisadas": total_revisadas,
        "total_nuevas": total_nuevas,
        "errores": errores,
    }
    LOGGER.info("Proceso finalizado resumen=%s", resumen)
    return resumen


if __name__ == "__main__":
    setup_logging(
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_file=os.getenv("LOG_FILE", str(DEFAULT_LOG_FILE)),
    )
    create_db()
    procesar_noticias()
