import logging
import os
import time
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
from services.webhook_dispatcher import dispatch_webhooks
from utils import extraer_metadatos_batch, score_noticia, setup_logging


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_LOG_FILE = BASE_DIR / "logs" / "news_scraper.log"
LOGGER = logging.getLogger("news_scraper")


def _resumen_delivery(delivery: dict[str, object]) -> str:
    """
    Aplana el resultado del envío para loguearlo.

    El dict crudo trae la respuesta completa de Evolution API por usuario, que
    incluye el texto íntegro de cada mensaje y el número de teléfono. Eso no
    aporta nada al log y lo vuelve ilegible, así que aquí solo queda el conteo
    y el estado por usuario.
    """
    usuarios = delivery.get("usuarios") or []
    detalle = " ".join(
        f"{u.get('usuario')}={u.get('status')}({u.get('enviadas')})"
        for u in usuarios
        if isinstance(u, dict)
    )
    return f"envios={delivery.get('total_envios', 0)} {detalle}".strip()


def _run_scraper(ScraperClass: type[BaseScraper]) -> tuple[str, list[NoticiaSchema], Exception | None]:
    """
    Ejecuta un scraper con reintentos.

    La mayoría de las fallas históricas son timeouts transitorios de Playwright
    (`Page.goto`, `wait_for_selector`) y 5xx puntuales de RSS, no errores de
    parseo: reintentar recupera la fuente en vez de perder la corrida entera.
    """
    scraper = ScraperClass()
    ultimo_error: Exception | None = None

    for intento in range(1, ENV.SCRAPER_MAX_INTENTOS + 1):
        try:
            noticias = scraper.fetch()
            if intento > 1:
                LOGGER.info(
                    "Scraper recuperado tras reintento fuente=%s intento=%s",
                    scraper.source,
                    intento,
                )
            return scraper.source, noticias, None
        except Exception as e:
            ultimo_error = e
            if intento < ENV.SCRAPER_MAX_INTENTOS:
                espera = ENV.SCRAPER_BACKOFF_SEGUNDOS * intento
                LOGGER.warning(
                    "Scraper falló fuente=%s intento=%s/%s error=%s; reintenta en %ss",
                    scraper.source,
                    intento,
                    ENV.SCRAPER_MAX_INTENTOS,
                    e,
                    espera,
                )
                time.sleep(espera)

    LOGGER.error(
        "Scraper agotó reintentos fuente=%s intentos=%s error=%s",
        scraper.source,
        ENV.SCRAPER_MAX_INTENTOS,
        ultimo_error,
    )
    return scraper.source, [], ultimo_error


def procesar_noticias(
    trigger: str = "manual",
    scrapers: list[type[BaseScraper]] | None = None,
) -> dict[str, object]:
    """
    Ejecuta el pipeline completo sobre `scrapers` (por defecto, todas las
    fuentes). Ver `ENV.GRUPOS_SCRAPERS` para los grupos por cadencia.
    """
    scrapers = ENV.SCRAPERS if scrapers is None else scrapers
    session = next(get_session())
    total_nuevas = 0
    noticias_nuevas: list[Noticia] = []
    errores: list[dict[str, str]] = []

    scrape_run = ScrapeRun(
        trigger=trigger,
        total_sources=len(scrapers),
        status="running",
    )
    session.add(scrape_run)
    session.commit()
    session.refresh(scrape_run)

    workers = max(1, min(len(scrapers), ENV.MAX_SCRAPER_WORKERS))
    LOGGER.info(
        "Iniciando proceso de scraping con %s fuentes (paralelo, workers=%s)",
        len(scrapers),
        workers,
    )

    # Phase 1: run all scrapers concurrently
    raw_results: dict[str, tuple[list[NoticiaSchema], Exception | None]] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_run_scraper, cls): cls for cls in scrapers}
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
    for ScraperClass in scrapers:
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

    for ScraperClass in scrapers:
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

    # Phase 4: una sola visita por candidata para bajada e imagen
    all_candidates = [n for cands in source_candidates.values() for n in cands]
    meta_map = (
        extraer_metadatos_batch([n.url for n in all_candidates], concurrency=8)
        if all_candidates
        else {}
    )

    # Phase 5: score, save, and record ScrapeRunSource per source
    for ScraperClass in scrapers:
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
                meta = meta_map.get(noticia.url)
                excerpt = (meta.excerpt if meta else None) or noticia.excerpt
                score = score_noticia(
                    noticia.title,
                    noticia.url,
                    noticia.source,
                    excerpt or "",
                )

                if score < ENV.SCORE_MINIMO:
                    continue

                # Los feeds sin imagen (Peru Retail, Expansion) la dejan en
                # None y aqui se completa con la og:image de la nota. Si no
                # hay ninguna de las dos se descarta: `noticia.img` es NOT
                # NULL y el envio por WhatsApp la manda como portada.
                img = noticia.img or (meta.img if meta else None)
                if not img:
                    LOGGER.info(
                        "Noticia sin imagen omitida fuente=%s url=%s",
                        noticia.source,
                        noticia.url,
                    )
                    continue

                db_noticia = Noticia(
                    scrape_run_id=scrape_run.id,
                    title=noticia.title,
                    url=noticia.url,
                    img=img,
                    date_preview=noticia.date_preview,
                    source=noticia.source,
                    country=noticia.country,
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
                    noticias_nuevas.append(db_noticia)
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

    if noticias_nuevas:
        dispatch_webhooks(session, scrape_run.id, noticias_nuevas)

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
    LOGGER.info(
        "Proceso finalizado scrape_run_id=%s revisadas=%s nuevas=%s errores=%s delivery=%s",
        scrape_run.id,
        total_revisadas,
        total_nuevas,
        len(errores),
        _resumen_delivery(delivery),
    )
    return resumen


if __name__ == "__main__":
    create_db()
    setup_logging(
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_file=os.getenv("LOG_FILE", str(DEFAULT_LOG_FILE)),
    )

    grupo = os.getenv("SCRAPER_GRUPO", "todos").strip().lower()
    if grupo not in ENV.GRUPOS_SCRAPERS:
        raise SystemExit(
            f"SCRAPER_GRUPO={grupo!r} no es válido. "
            f"Opciones: {', '.join(sorted(ENV.GRUPOS_SCRAPERS))}"
        )

    LOGGER.info("Grupo de fuentes=%s", grupo)
    procesar_noticias(
        trigger=os.getenv("SCRAPER_TRIGGER", "manual"),
        scrapers=ENV.GRUPOS_SCRAPERS[grupo],
    )
