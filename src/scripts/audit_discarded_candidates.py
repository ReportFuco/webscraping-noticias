from collections import defaultdict

from scrapers import (
    CCSScraper,
    CencosudMediosScraper,
    DFRetailScraper,
    LaTerceraPulsoScraper,
    PortalInnovaScraper,
    SMUScraper,
    WalmartChileScraper,
)
from utils import extraer_bajadas_batch, score_noticia

SCRAPERS = [
    DFRetailScraper,
    CCSScraper,
    WalmartChileScraper,
    CencosudMediosScraper,
    SMUScraper,
    PortalInnovaScraper,
    LaTerceraPulsoScraper,
]


def main() -> None:
    kept = []
    discarded = []
    by_source = defaultdict(lambda: {"kept": 0, "discarded": 0})

    for scraper_cls in SCRAPERS:
        scraper = scraper_cls()
        try:
            noticias = scraper.fetch()
        except Exception as exc:
            print(f"ERROR source={scraper.source} error={exc}")
            continue

        excerpt_map = extraer_bajadas_batch([n.url for n in noticias], concurrency=4) if noticias else {}

        for n in noticias:
            excerpt = excerpt_map.get(n.url) or n.excerpt or ""
            score = score_noticia(n.title, n.url, n.source, excerpt)
            item = {
                "source": n.source,
                "score": score,
                "title": n.title,
                "url": n.url,
                "excerpt": excerpt[:220],
            }
            if score >= 3:
                kept.append(item)
                by_source[n.source]["kept"] += 1
            else:
                discarded.append(item)
                by_source[n.source]["discarded"] += 1

    print("=== RESUMEN POR FUENTE ===")
    for source, stats in sorted(by_source.items()):
        print(f"{source}: kept={stats['kept']} discarded={stats['discarded']}")

    print("\n=== MEJORES DESCARTADAS (score 2 primero) ===")
    discarded_sorted = sorted(discarded, key=lambda x: (-x["score"], x["source"], x["title"]))
    for item in discarded_sorted[:25]:
        print(f"[{item['source']}] score={item['score']} | {item['title']}")
        print(f" url={item['url']}")
        if item['excerpt']:
            print(f" excerpt={item['excerpt']}")
        print("-" * 100)

    print("\n=== MANTENIDAS (para contraste) ===")
    kept_sorted = sorted(kept, key=lambda x: (-x["score"], x["source"], x["title"]))
    for item in kept_sorted[:20]:
        print(f"[{item['source']}] score={item['score']} | {item['title']}")
        print(f" url={item['url']}")
        if item['excerpt']:
            print(f" excerpt={item['excerpt']}")
        print("-" * 100)


if __name__ == "__main__":
    main()
