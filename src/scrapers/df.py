from typing import List
import re

import httpx

from .base import BaseScraper
from schemas import NoticiaSchema


class DFScraper(BaseScraper):
    source = "df"
    URL = "https://www.df.cl/mercados"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    }

    def _absolute_url(self, value: str | None) -> str | None:
        if not value:
            return None
        if value.startswith("http://") or value.startswith("https://"):
            return value
        if value.startswith("/"):
            return f"https://www.df.cl{value}"
        return f"https://www.df.cl/{value.lstrip('/')}"

    def _extract_date_from_image_url(self, img_url: str | None) -> str | None:
        if not img_url:
            return None
        match = re.search(r"/site/artic/(\d{4})(\d{2})(\d{2})/", img_url)
        if match:
            year, month, day = match.groups()
            return f"{day}/{month}/{year}"
        return None

    def _clean_text(self, value: str | None) -> str | None:
        if not value:
            return None
        text = re.sub(r"<[^>]+>", " ", value)
        text = re.sub(r"\s+", " ", text).strip()
        return text or None

    def fetch(self) -> List[NoticiaSchema]:
        noticias: List[NoticiaSchema] = []
        seen_urls: set[str] = set()

        with httpx.Client(headers=self.HEADERS, follow_redirects=True, timeout=30) as client:
            response = client.get(self.URL)
            response.raise_for_status()
            raw_html = response.text

        article_blocks = re.findall(r"<article class=\"card.*?</article>", raw_html, re.IGNORECASE | re.DOTALL)
        self.logger.info("Noticias encontradas: %s", len(article_blocks))

        for block in article_blocks:
            link_match = re.search(r'<a href="([^"]+)"', block, re.IGNORECASE)
            img_match = re.search(r'<img src="([^"]+)"', block, re.IGNORECASE)
            title_match = re.search(r'<h3 class="card__title[^>]*>(.*?)</h3>', block, re.IGNORECASE | re.DOTALL)
            if not title_match:
                title_match = re.search(r'<h2 class="slider__title">\s*<a[^>]*>(.*?)</a>\s*</h2>', block, re.IGNORECASE | re.DOTALL)
            desc_match = re.search(r'<p class="card__description">(.*?)</p>', block, re.IGNORECASE | re.DOTALL)

            url = self._absolute_url(link_match.group(1)) if link_match else None
            img_url = self._absolute_url(img_match.group(1)) if img_match else None
            title = self._clean_text(title_match.group(1)) if title_match else None
            excerpt = self._clean_text(desc_match.group(1)) if desc_match else None
            date_preview = self._extract_date_from_image_url(img_url)

            if not url or url in seen_urls:
                continue
            if "/mercados/" not in url:
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
                    excerpt=excerpt,
                )
            )
            seen_urls.add(url)

        return noticias
