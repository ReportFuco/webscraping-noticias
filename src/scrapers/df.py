from datetime import date
from typing import List
import re

import httpx

from .base import BaseScraper
from schemas import NoticiaSchema


class DFScraper(BaseScraper):
    source = "df"
    URL = "https://www.df.cl/mercados"
    BASE_URL = "https://www.df.cl"

    def _extract_date_from_image_url(self, img_url: str | None) -> date | None:
        if not img_url:
            return None
        match = re.search(r"/site/artic/(\d{4})(\d{2})(\d{2})/", img_url)
        if match:
            year, month, day = match.groups()
            try:
                return date(int(year), int(month), int(day))
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
