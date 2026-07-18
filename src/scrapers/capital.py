from __future__ import annotations

import re
from datetime import date
from typing import List

import httpx

from .base import BaseScraper
from schemas import NoticiaSchema


class CapitalScraper(BaseScraper):
    source = "capital"
    URL = "https://www.df.cl/capital"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    }
    ARTICLE_RE = re.compile(r'<article class="card.*?</article>', re.IGNORECASE | re.DOTALL)
    LINK_RE = re.compile(r'<a href="([^"]+)"', re.IGNORECASE)
    IMG_RE = re.compile(r'<img src="([^"]+)"', re.IGNORECASE)
    TITLE_RE = re.compile(r'<h3 class="card__title[^>]*>(.*?)</h3>', re.IGNORECASE | re.DOTALL)
    DESC_RE = re.compile(r'<p class="card__description">(.*?)</p>', re.IGNORECASE | re.DOTALL)
    IMG_DATE_RE = re.compile(r"/site/artic/(\d{4})(\d{2})(\d{2})/")
    SPAN_DATE_RE = re.compile(r'<span class="card__date">(\d{2})/(\d{2})/(\d{4})</span>')

    def _absolute_url(self, value: str | None) -> str | None:
        if not value:
            return None
        if value.startswith("http://") or value.startswith("https://"):
            return value
        if value.startswith("/"):
            return f"https://www.df.cl{value}"
        return f"https://www.df.cl/{value.lstrip('/')}"

    def _clean_text(self, value: str | None) -> str | None:
        if not value:
            return None
        text = re.sub(r"<[^>]+>", " ", value)
        text = re.sub(r"\s+", " ", text).strip()
        return text or None

    def _extract_date(self, img_url: str | None, block: str) -> date | None:
        if img_url:
            match = self.IMG_DATE_RE.search(img_url)
            if match:
                try:
                    return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
                except ValueError:
                    pass
        match = self.SPAN_DATE_RE.search(block)
        if match:
            try:
                return date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
            except ValueError:
                pass
        return None

    def fetch(self) -> List[NoticiaSchema]:
        noticias: List[NoticiaSchema] = []
        seen_urls: set[str] = set()

        with httpx.Client(headers=self.HEADERS, follow_redirects=True, timeout=30) as client:
            response = client.get(self.URL)
            response.raise_for_status()
            raw_html = response.text

        article_blocks = self.ARTICLE_RE.findall(raw_html)
        self.logger.info("Noticias encontradas: %s", len(article_blocks))

        for block in article_blocks:
            link_match = self.LINK_RE.search(block)
            img_match = self.IMG_RE.search(block)
            title_match = self.TITLE_RE.search(block)
            desc_match = self.DESC_RE.search(block)

            url = self._absolute_url(link_match.group(1)) if link_match else None
            img_url = self._absolute_url(img_match.group(1)) if img_match else None
            title = self._clean_text(title_match.group(1)) if title_match else None
            excerpt = self._clean_text(desc_match.group(1)) if desc_match else None
            date_preview = self._extract_date(img_url, block)

            if not url or url in seen_urls:
                continue
            if "/capital/" not in url:
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
