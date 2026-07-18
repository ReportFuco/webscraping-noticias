from __future__ import annotations

import html
import re
from datetime import date, datetime
from typing import List

import httpx

from .base import BaseScraper
from schemas import NoticiaSchema


class RetailActualScraper(BaseScraper):
    source = "retailactual"
    country = "ES"
    URL = "https://www.retailactual.com/noticias"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    }
    BLOCK_RE = re.compile(r'<article class="new">.*?</article>', re.DOTALL)
    TITLE_RE = re.compile(r'<h2>(.*?)</h2></a>')
    URL_RE = re.compile(r'<a href="([^"]+)"[^>]*>\s*<h2>')
    IMG_RE = re.compile(r'<img src="([^"]+)"')
    DATE_URL_RE = re.compile(r"/noticias/(\d{8})/")
    EXCERPT_RE = re.compile(r"</div>\s*<p>(.*?)</p>", re.DOTALL)

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
        try:
            return datetime.strptime(value, "%Y%m%d").date()
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
            url_match = self.URL_RE.search(block)
            img_match = self.IMG_RE.search(block)
            date_match = self.DATE_URL_RE.search(block)
            excerpt_match = self.EXCERPT_RE.search(block)

            title = self._clean_text(title_match.group(1)) if title_match else None
            url = url_match.group(1) if url_match else None
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
                    country=self.country,
                    excerpt=excerpt,
                )
            )
            seen_urls.add(url)

        return noticias
