import argparse
import logging
import os
from pathlib import Path

from sqlmodel import select

from database import create_db, get_session
from models import Noticia
from utils import extraer_bajada, setup_logging


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_LOG_FILE = BASE_DIR / "logs" / "backfill_excerpts.log"
LOGGER = logging.getLogger("backfill_excerpts")


def backfill_excerpts(limit: int = 100, source: str | None = None, retry_all: bool = False) -> dict:
    session = next(get_session())

    statement = select(Noticia)

    if not retry_all:
        statement = statement.where((Noticia.excerpt == None) | (Noticia.excerpt == ""))

    if source:
        statement = statement.where(Noticia.source == source)

    statement = statement.order_by(Noticia.created_at.desc()).limit(limit)
    noticias = session.exec(statement).all()

    revisadas = 0
    actualizadas = 0
    sin_cambios = 0
    errores = 0

    LOGGER.info(
        "Iniciando backfill de excerpts limit=%s source=%s retry_all=%s seleccionadas=%s",
        limit,
        source,
        retry_all,
        len(noticias),
    )

    for noticia in noticias:
        revisadas += 1

        try:
            excerpt = extraer_bajada(noticia.url)
        except Exception as exc:
            errores += 1
            LOGGER.exception("Error extrayendo excerpt noticia_id=%s url=%s", noticia.id, noticia.url)
            continue

        if not excerpt:
            sin_cambios += 1
            LOGGER.info(
                "Sin excerpt noticia_id=%s fuente=%s title=%s",
                noticia.id,
                noticia.source,
                noticia.title[:80],
            )
            continue

        if noticia.excerpt == excerpt:
            sin_cambios += 1
            continue

        noticia.excerpt = excerpt
        session.add(noticia)
        session.commit()
        actualizadas += 1

        LOGGER.info(
            "Excerpt actualizado noticia_id=%s fuente=%s title=%s",
            noticia.id,
            noticia.source,
            noticia.title[:80],
        )

    resumen = {
        "revisadas": revisadas,
        "actualizadas": actualizadas,
        "sin_cambios": sin_cambios,
        "errores": errores,
    }
    LOGGER.info("Backfill finalizado resumen=%s", resumen)
    return resumen


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rellena excerpts faltantes en noticias ya guardadas")
    parser.add_argument("--limit", type=int, default=100, help="Máximo de noticias a procesar")
    parser.add_argument("--source", type=str, default=None, help="Filtrar por fuente")
    parser.add_argument(
        "--retry-all",
        action="store_true",
        help="Reintenta extracción incluso si la noticia ya tiene excerpt",
    )
    args = parser.parse_args()

    setup_logging(
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_file=os.getenv("LOG_FILE", str(DEFAULT_LOG_FILE)),
    )
    create_db()
    backfill_excerpts(limit=args.limit, source=args.source, retry_all=args.retry_all)
