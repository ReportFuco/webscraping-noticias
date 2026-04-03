from __future__ import annotations

import html
import re
from datetime import datetime
from typing import List
from xml.etree import ElementTree as ET

import httpx

from .base import BaseScraper
from schemas import NoticiaSchema


class GestionScraper(BaseScraper):
    source = "gestion"
    URL = "https://gestion.pe/arcio/rss/"
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

    def _parse_pub_date(self, value: str | None) -> str | None:
        if not value:
            return None
        value = value.strip()
        for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S GMT"):
            try:
                return datetime.strptime(value, fmt).strftime("%d/%m/%Y")
            except ValueError:
                continue
        return None

    def _extract_image(self, item: ET.Element) -> str | None:
        for child in item:
            tag = child.tag.lower()
            if tag.endswith("content"):
                url = child.attrib.get("url")
                if url:
                    return url
            if tag.endswith("thumbnail"):
                url = child.attrib.get("url")
                if url:
                    return url
        enclosure = item.find("enclosure")
        if enclosure is not None:
            return enclosure.attrib.get("url")
        return None

    def fetch(self) -> List[NoticiaSchema]:
        with httpx.Client(headers=self.HEADERS, follow_redirects=True, timeout=30) as client:
            response = client.get(self.URL)
            response.raise_for_status()
            root = ET.fromstring(response.text)

        noticias: list[NoticiaSchema] = []
        seen_urls: set[str] = set()

        for item in root.findall("./channel/item"):
            title = self._clean_text(item.findtext("title"))
            url = self._clean_text(item.findtext("link"))
            excerpt = self._clean_text(item.findtext("description"))
            pub_date = self._clean_text(item.findtext("pubDate"))
            img = self._extract_image(item)
            date_preview = self._parse_pub_date(pub_date)

            if not title or not url or not img or not date_preview:
                continue
            if url in seen_urls:
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
