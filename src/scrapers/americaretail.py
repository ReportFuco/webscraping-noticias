from __future__ import annotations

import html
import re
from datetime import date
from typing import List

import httpx

from .base import BaseScraper
from schemas import NoticiaSchema

_MESES: dict[str, int] = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}


class AmericaRetailScraper(BaseScraper):
    source = "americaretail"
    URL = "https://americaretail-malls.com/"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    }
    BLOCK_RE = re.compile(r'<article class="jeg_post[^"]*"[^>]*>.*?</article>', re.DOTALL)
    TITLE_RE = re.compile(r'<h[23] class="jeg_post_title">\s*<a href="([^"]+)"[^>]*>(.*?)</a>', re.DOTALL)
    IMG_RE = re.compile(r'data-src="([^"]+)"')
    DATE_RE = re.compile(r'<div class="jeg_meta_date"><a[^>]*>\s*<i[^>]*></i>\s*([^<]+)</a>')
    EXCERPT_RE = re.compile(r'<div class="jeg_post_excerpt">(.*?)</div>', re.DOTALL)

    def _clean_text(self, value: str | None) -> str | None:
        if not value:
            return None
        text = html.unescape(value)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text or None

    def _parse_date(self, value: str | None) -> date | None:
        if not value:
            return None
        match = re.search(r"([A-Za-zÀ-ÿ]+)\s+(\d{1,2}),\s*(\d{4})", value.strip())
        if not match:
            return None
        month = _MESES.get(match.group(1).lower())
        if not month:
            return None
        try:
            return date(int(match.group(3)), month, int(match.group(2)))
        except ValueError:
            return None

    def fetch(self) -> List[NoticiaSchema]:
        with httpx.Client(headers=self.HEADERS, follow_redirects=True, timeout=30) as client:
            response = client.get(self.URL)
            response.raise_for_status()
            raw_html = response.text

        blocks = self.BLOCK_RE.findall(raw_html)
        self.logger.info("Noticias encontradas: %s", len(blocks))

        noticias: List[NoticiaSchema] = []
        seen_urls: set[str] = set()

        for block in blocks:
            title_match = self.TITLE_RE.search(block)
            img_match = self.IMG_RE.search(block)
            date_match = self.DATE_RE.search(block)
            excerpt_match = self.EXCERPT_RE.search(block)

            url = title_match.group(1) if title_match else None
            title = self._clean_text(title_match.group(2)) if title_match else None
            img_url = img_match.group(1) if img_match else None
            excerpt = self._clean_text(excerpt_match.group(1)) if excerpt_match else None
            date_preview = self._parse_date(date_match.group(1)) if date_match else None

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
                    excerpt=excerpt,
                )
            )
            seen_urls.add(url)

        return noticias
