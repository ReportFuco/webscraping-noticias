from __future__ import annotations

import argparse
import csv
import os
from datetime import datetime
from io import BytesIO
from pathlib import Path

import config as ENV
from utils import BotWhatsApp, extraer_bajadas_batch, score_noticia, setup_logging


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_DESTINATION = "56978086719"


def _build_rows() -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []
    seen_urls: set[str] = set()

    for scraper_cls in ENV.SCRAPERS:
        scraper = scraper_cls()
        try:
            noticias = scraper.fetch()
        except Exception as exc:
            rows.append(
                {
                    "source": scraper.source,
                    "country": scraper.country,
                    "title": f"[ERROR] {exc}",
                    "url": "",
                    "date_preview": "",
                    "excerpt": "",
                    "score": -1,
                    "would_pass_filter": "error",
                }
            )
            continue

        candidatas = []
        for noticia in noticias:
            if noticia.url in seen_urls:
                continue
            seen_urls.add(noticia.url)
            candidatas.append(noticia)

        excerpt_map = extraer_bajadas_batch([n.url for n in candidatas], concurrency=4) if candidatas else {}

        for noticia in candidatas:
            excerpt = excerpt_map.get(noticia.url) or noticia.excerpt or ""
            score = score_noticia(
                noticia.title,
                noticia.url,
                noticia.source,
                excerpt,
            )
            rows.append(
                {
                    "source": noticia.source,
                    "country": noticia.country,
                    "title": noticia.title,
                    "url": noticia.url,
                    "date_preview": noticia.date_preview or "",
                    "excerpt": excerpt,
                    "score": score,
                    "would_pass_filter": "yes" if score >= ENV.SCORE_MINIMO else "no",
                }
            )

    rows.sort(
        key=lambda row: (
            0 if row["would_pass_filter"] == "yes" else 1,
            -(int(row["score"]) if isinstance(row["score"], int) else -1),
            str(row["source"]),
            str(row["title"]),
        )
    )
    return rows


def _build_csv_buffer(rows: list[dict[str, str | int]]) -> tuple[BytesIO, str]:
    now = datetime.now()
    filename = f"scrape-review-{now.strftime('%Y-%m-%d-%H%M%S')}.csv"

    fieldnames = [
        "source",
        "country",
        "title",
        "url",
        "date_preview",
        "excerpt",
        "score",
        "would_pass_filter",
    ]

    text_buffer = BytesIO()
    content = []
    import io
    string_buffer = io.StringIO()
    writer = csv.DictWriter(
        string_buffer,
        fieldnames=fieldnames,
        delimiter=";",
        quoting=csv.QUOTE_MINIMAL,
    )
    writer.writeheader()
    writer.writerows(rows)
    content = string_buffer.getvalue().encode("utf-8-sig")
    text_buffer.write(content)
    text_buffer.seek(0)
    return text_buffer, filename


def main(destination: str = DEFAULT_DESTINATION, send: bool = True) -> int:
    rows = _build_rows()
    csv_buffer, file_name = _build_csv_buffer(rows)

    total = len(rows)
    passing = sum(1 for row in rows if row["would_pass_filter"] == "yes")
    errors = sum(1 for row in rows if row["would_pass_filter"] == "error")

    print(f"CSV generado en memoria: {file_name}")
    print(f"Total filas: {total}")
    print(f"Pasan filtro: {passing}")
    print(f"Errores fuente: {errors}")

    if not send:
        return 0

    bot = BotWhatsApp(**ENV.EVOLUTION_CREDENCIALS)
    caption = (
        f"Reporte manual scrape noticias. Total: {total}. "
        f"Pasan filtro: {passing}. Errores fuente: {errors}."
    )
    response = bot.enviar_documento(
        numero=destination,
        buffer=csv_buffer,
        file_name=file_name,
        caption=caption,
        mimetype="text/csv",
    )

    print(f"Envio ok={response.get('ok')} status={response.get('status_code')}")
    if not response.get("ok"):
        print(f"Error envio: {response.get('error')}")
        return 1

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Exporta noticias scrapeadas a CSV y las envía por WhatsApp")
    parser.add_argument("--to", default=DEFAULT_DESTINATION, help="Número destino en formato 569XXXXXXXX")
    parser.add_argument("--no-send", action="store_true", help="Genera el CSV pero no lo envía")
    args = parser.parse_args()

    setup_logging(
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_file=os.getenv("LOG_FILE", str(BASE_DIR / "logs" / "export_scrape_review_csv.log")),
    )
    raise SystemExit(main(destination=args.to, send=not args.no_send))
