from .base import BaseScraper
from schemas import NoticiaSchema
from utils import normalizar_fecha
import httpx
import html
import re


class BioBioScraper(BaseScraper):
    source = "biobiochile"
    URL = "https://www.biobiochile.cl/lista/categorias/nacional"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    }

    def _clean_text(self, value: str | None) -> str | None:
        if not value:
            return None
        text = html.unescape(value)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text or None

    def fetch(self) -> list[NoticiaSchema]:
        noticias: list[NoticiaSchema] = []
        seen_urls: set[str] = set()

        with httpx.Client(headers=self.HEADERS, follow_redirects=True, timeout=30) as client:
            response = client.get(self.URL)
            response.raise_for_status()
            raw_html = response.text

        article_blocks = re.findall(
            r'<article class="article article-horizontal article-with-square.*?</article>',
            raw_html,
            re.IGNORECASE | re.DOTALL,
        )
        self.logger.info("Noticias encontradas: %s", len(article_blocks))

        for block in article_blocks:
            link_match = re.search(r'<a\s+href="(https://www\.biobiochile\.cl/[^"]+)"', block, re.IGNORECASE)
            title_match = re.search(r'<h2 class="article-title"[^>]*>(.*?)</h2>', block, re.IGNORECASE | re.DOTALL)
            img_match = re.search(r'style="background-image:\s*url\((.*?)\)"', block, re.IGNORECASE | re.DOTALL)
            date_match = re.search(r'<div class="article-date-hour">\s*(.*?)\s*</div>', block, re.IGNORECASE | re.DOTALL)

            url = link_match.group(1).strip() if link_match else None
            title = self._clean_text(title_match.group(1)) if title_match else None
            img_url = self._clean_text(img_match.group(1)) if img_match else None
            raw_date = self._clean_text(date_match.group(1)) if date_match else None
            date_preview = normalizar_fecha(raw_date) if raw_date else None

            if not url or url in seen_urls:
                continue
            if not title or not img_url or not date_preview:
                continue

            noticias.append(
                NoticiaSchema(
                    title=title,
                    url=url,
                    img=img_url,
                    date_preview=date_preview,
                    source=self.source,
                )
            )
            seen_urls.add(url)

        return noticias
