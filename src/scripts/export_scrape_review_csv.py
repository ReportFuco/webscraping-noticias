from __future__ import annotations

import argparse
import csv
import os
from datetime import datetime
from pathlib import Path

import config as ENV
from utils import BotWhatsApp, extraer_bajadas_batch, score_noticia, setup_logging


BASE_DIR = Path(__file__).resolve().parent.parent.parent
EXPORTS_DIR = BASE_DIR / "exports"
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


def _write_csv(rows: list[dict[str, str | int]]) -> Path:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    filename = f"scrape-review-{now.strftime('%Y-%m-%d-%H%M%S')}.csv"
    path = EXPORTS_DIR / filename

    fieldnames = [
        "source",
        "title",
        "url",
        "date_preview",
        "excerpt",
        "score",
        "would_pass_filter",
    ]

    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            delimiter=";",
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
        writer.writerows(rows)

    return path


def main(destination: str = DEFAULT_DESTINATION, send: bool = True) -> int:
    rows = _build_rows()
    csv_path = _write_csv(rows)

    total = len(rows)
    passing = sum(1 for row in rows if row["would_pass_filter"] == "yes")
    errors = sum(1 for row in rows if row["would_pass_filter"] == "error")

    print(f"CSV generado: {csv_path}")
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
        path_archivo=str(csv_path),
        file_name=csv_path.name,
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
