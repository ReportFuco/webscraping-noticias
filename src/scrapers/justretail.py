from __future__ import annotations

import re
from datetime import date, datetime
from typing import List

import httpx

from .base import BaseScraper
from schemas import NoticiaSchema


class JustRetailScraper(BaseScraper):
    source = "justretail"
    country = "ES"
    URL = "https://www.justretail.news/"
    BLOCK_RE = re.compile(
        r'<div class="td_module_flex td_module_flex_1[^"]*"[^>]*>.*?</h3>.*?</div>\s*</div>\s*</div>',
        re.DOTALL,
    )
    URL_RE = re.compile(r'<div class="td-module-thumb"><a href="([^"]+)"')
    IMG_RE = re.compile(r"background-image: url\('([^']+)'\)")
    IMG_LAZY_RE = re.compile(r'data-img-url="([^"]+)"')
    TITLE_RE = re.compile(
        r'<h3 class="entry-title td-module-title"><a[^>]*>(.*?)</a></h3>', re.DOTALL
    )
    DATE_RE = re.compile(
        r'<time class="entry-date updated td-module-date" datetime="([^"]+)"'
    )
    EXCERPT_RE = re.compile(r'<div class="td-excerpt">(.*?)</div>', re.DOTALL)

    def _parse_date(self, value: str | None) -> date | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value).date()
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
            url_match = self.URL_RE.search(block)
            img_match = self.IMG_RE.search(block) or self.IMG_LAZY_RE.search(block)
            title_match = self.TITLE_RE.search(block)
            date_match = self.DATE_RE.search(block)
            excerpt_match = self.EXCERPT_RE.search(block)

            url = url_match.group(1) if url_match else None
            img_url = img_match.group(1) if img_match else None
            title = self._clean_text(title_match.group(1)) if title_match else None
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
