from __future__ import annotations

import html
import json
import re
from typing import List

from playwright.sync_api import sync_playwright

from .base import BaseScraper
from schemas import NoticiaSchema
from utils import normalizar_fecha


class LaTerceraPulsoScraper(BaseScraper):
    source = "latercera_pulso"
    URL = "https://www.latercera.com/canal/pulso/"
    BASE_URL = "https://www.latercera.com"
    MAX_ITEMS = 20
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )

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

    def _clean_text(self, value: str | None) -> str | None:
        if not value:
            return None
        text = html.unescape(value)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text or None

    def _extract_json_objects(self, raw_html: str) -> list[dict]:
        objects: list[dict] = []
        pattern = r'\{"_id":"[^"]+","canonical_url":"/pulso/noticia/[^"]+"'

        for match in re.finditer(pattern, raw_html):
            start = match.start()
            brace_count = 0
            in_string = False
            escaped = False
            end = None

            for i in range(start, len(raw_html)):
                ch = raw_html[i]
                if in_string:
                    if escaped:
                        escaped = False
                    elif ch == "\\":
                        escaped = True
                    elif ch == '"':
                        in_string = False
                else:
                    if ch == '"':
                        in_string = True
                    elif ch == '{':
                        brace_count += 1
                    elif ch == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end = i + 1
                            break

            if end is None:
                continue

            chunk = raw_html[start:end]
            try:
                obj = json.loads(chunk)
            except Exception:
                continue

            if obj.get("taxonomy", {}).get("primary_section", {}).get("path") != "/pulso":
                continue
            objects.append(obj)

        return objects

    def fetch(self) -> List[NoticiaSchema]:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=self.USER_AGENT, locale="es-CL")
            page = context.new_page()
            page.goto(self.URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2500)
            raw_html = page.content()
            browser.close()

        raw_objects = self._extract_json_objects(raw_html)
        self.logger.info("Noticias encontradas: %s", len(raw_objects))

        noticias: list[NoticiaSchema] = []
        seen_urls: set[str] = set()

        for item in raw_objects:
            url = self._absolute_url(
                item.get("websites", {}).get("la-tercera", {}).get("website_url")
                or item.get("canonical_url")
            )
            title = self._clean_text(item.get("headlines", {}).get("basic"))
            excerpt = self._clean_text(item.get("description", {}).get("basic"))
            img = self._absolute_url(item.get("promo_items", {}).get("basic", {}).get("url"))
            date_preview = normalizar_fecha(item.get("first_publish_date") or item.get("last_updated_date") or "")

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

        return noticias
