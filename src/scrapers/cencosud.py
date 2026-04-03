from __future__ import annotations

import html
import re
from typing import List

import httpx

from .base import BaseScraper
from schemas import NoticiaSchema


class CencosudMediosScraper(BaseScraper):
    source = "cencosud"
    URL = "https://www.cencosud.com/centro_de_medios"
    BASE_URL = "https://www.cencosud.com"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    }
    MAX_ITEMS = 20

    def _clean_text(self, value: str | None) -> str | None:
        if not value:
            return None
        text = html.unescape(value)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text or None

    def _absolute_url(self, value: str | None) -> str | None:
        if not value:
            return None
        if value.startswith(("http://", "https://")):
            return value
        if value.startswith("//"):
            return f"https:{value}"
        if value.startswith("/"):
            return f"{self.BASE_URL}{value}"
        return f"{self.BASE_URL}/{value.lstrip('/')}"

    def fetch(self) -> List[NoticiaSchema]:
        with httpx.Client(headers=self.HEADERS, follow_redirects=True, timeout=30) as client:
            response = client.get(self.URL)
            response.raise_for_status()
            raw_html = response.text

        blocks = re.findall(
            r'<div class="(?:three-item-card-outer|category-card-outer)">\s*<div class="category-card">(.*?)</div>\s*</div>',
            raw_html,
            re.IGNORECASE | re.DOTALL,
        )

        noticias: list[NoticiaSchema] = []
        seen_urls: set[str] = set()

        for block in blocks:
            date_match = re.search(r'<h6 class="category-card-date">(.*?)</h6>', block, re.IGNORECASE | re.DOTALL)
            title_match = re.search(
                r'<h4 class="category-card-title">\s*<a href="([^"]+)"[^>]*title="([^"]+)"[^>]*>.*?</a>',
                block,
                re.IGNORECASE | re.DOTALL,
            )
            img_match = re.search(r'<img src="([^"]+)" class="(?:chart-card-img|category-card-img)"', block, re.IGNORECASE)
            excerpt_match = re.search(r'<p class="category-card-text">(.*?)</p>', block, re.IGNORECASE | re.DOTALL)

            url = self._absolute_url(title_match.group(1)) if title_match else None
            title = self._clean_text(title_match.group(2)) if title_match else None
            img = self._absolute_url(img_match.group(1)) if img_match else None
            excerpt = self._clean_text(excerpt_match.group(1)) if excerpt_match else None
            date_preview = self._clean_text(date_match.group(1)) if date_match else None

            if not url or url in seen_urls:
                continue
            if "/centro-de-medios/" not in url:
                continue
            if not title or not img or not date_preview:
                continue

            noticias.append(
                NoticiaSchema(
                    title=title,
                    url=url,
                    img=img,
                    date_preview=date_preview,
                    source=self.source,
                    excerpt=excerpt,
                )
            )
            seen_urls.add(url)

            if len(noticias) >= self.MAX_ITEMS:
                break

        self.logger.info("Noticias encontradas: %s", len(noticias))
        return noticias
