import argparse
import logging
import os
import time
from pathlib import Path

from config import SCRAPERS
from utils import setup_logging


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_LOG_FILE = BASE_DIR / "logs" / "test_scrapers.log"
LOGGER = logging.getLogger("test_scrapers")


def _available_scrapers() -> dict[str, type]:
    return {scraper.source: scraper for scraper in SCRAPERS}


def _validate_item(item) -> list[str]:
    errors: list[str] = []

    if not getattr(item, "title", None):
        errors.append("title vacío")
    if not getattr(item, "url", None):
        errors.append("url vacía")
    if not getattr(item, "img", None):
        errors.append("img vacía")
    if not getattr(item, "date_preview", None):
        errors.append("date_preview vacío")
    if not getattr(item, "source", None):
        errors.append("source vacío")

    url = getattr(item, "url", "") or ""
    img = getattr(item, "img", "") or ""
    if url and not url.startswith(("http://", "https://")):
        errors.append("url no absoluta")
    if img and not img.startswith(("http://", "https://")):
        errors.append("img no absoluta")

    return errors


def run_scraper_test(scraper_cls: type, sample_size: int = 3) -> dict:
    scraper = scraper_cls()
    started = time.perf_counter()

    try:
        items = scraper.fetch()
    except Exception as exc:
        elapsed = round(time.perf_counter() - started, 2)
        LOGGER.exception("Test falló fuente=%s tiempo=%ss", scraper.source, elapsed)
        return {
            "source": scraper.source,
            "ok": False,
            "count": 0,
            "elapsed": elapsed,
            "errors": [str(exc)],
            "sample": [],
        }

    elapsed = round(time.perf_counter() - started, 2)
    validation_errors: list[str] = []
    sample: list[dict] = []

    for index, item in enumerate(items[:sample_size], start=1):
        item_errors = _validate_item(item)
        if item_errors:
            validation_errors.extend([f"item#{index}: {err}" for err in item_errors])
        sample.append(
            {
                "title": (item.title or "")[:120],
                "url": item.url,
                "date_preview": str(item.date_preview),
                "excerpt": ((item.excerpt or "")[:160] if hasattr(item, "excerpt") else ""),
            }
        )

    ok = len(items) > 0 and not validation_errors
    LOGGER.info(
        "Test scraper fuente=%s ok=%s count=%s tiempo=%ss validation_errors=%s",
        scraper.source,
        ok,
        len(items),
        elapsed,
        len(validation_errors),
    )

    return {
        "source": scraper.source,
        "ok": ok,
        "count": len(items),
        "elapsed": elapsed,
        "errors": validation_errors,
        "sample": sample,
    }


def main(selected_sources: list[str] | None = None, sample_size: int = 3) -> int:
    scraper_map = _available_scrapers()

    if selected_sources:
        unknown = [source for source in selected_sources if source not in scraper_map]
        if unknown:
            LOGGER.error("Fuentes desconocidas: %s", ", ".join(unknown))
            return 2
        selected = [scraper_map[source] for source in selected_sources]
    else:
        selected = list(scraper_map.values())

    results = [run_scraper_test(scraper_cls, sample_size=sample_size) for scraper_cls in selected]

    print("\n=== RESULTADOS TEST SCRAPERS ===")
    for result in results:
        status = "OK" if result["ok"] else "FAIL"
        print(f"[{status}] {result['source']} | count={result['count']} | tiempo={result['elapsed']}s")
        if result["errors"]:
            for err in result["errors"][:10]:
                print(f"  - {err}")
        for sample in result["sample"]:
            print(f"  · {sample['title']}")

    total = len(results)
    failed = sum(1 for result in results if not result["ok"])
    print(f"\nResumen: {total - failed}/{total} scrapers OK")

    return 1 if failed else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prueba scrapers de forma independiente")
    parser.add_argument(
        "--source",
        action="append",
        dest="sources",
        help="Fuente específica a probar (repetible). Ej: --source walmartchile --source dfretail",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=3,
        help="Cantidad de ejemplos a mostrar por scraper",
    )
    args = parser.parse_args()

    setup_logging(
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_file=os.getenv("LOG_FILE", str(DEFAULT_LOG_FILE)),
    )
    raise SystemExit(main(selected_sources=args.sources, sample_size=args.sample_size))
