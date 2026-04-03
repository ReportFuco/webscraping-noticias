from __future__ import annotations

import html
import json
import re
from typing import List

from playwright.sync_api import sync_playwright

from .base import BaseScraper
from schemas import NoticiaSchema
from utils import normalizar_fecha


class SMUScraper(BaseScraper):
    source = "smu"
    URL = "https://www.smu.cl/noticias"
    BASE_URL = "https://www.smu.cl"
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
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                locale="es-CL",
            )
            page = context.new_page()
            page.goto(self.URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(1500)
            raw_html = page.content()
            browser.close()

        match = re.search(
            r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
            raw_html,
            re.IGNORECASE | re.DOTALL,
        )
        if not match:
            raise RuntimeError("No se encontró __NEXT_DATA__ en SMU")

        data = json.loads(match.group(1))
        items = data.get("props", {}).get("pageProps", {}).get("paginaNoticias", {}).get("elementosTop", [])

        noticias: list[NoticiaSchema] = []
        seen_urls: set[str] = set()

        for item in items:
            fields = item.get("fields", {})
            file_url = (
                fields.get("imagen", {})
                .get("fields", {})
                .get("file", {})
                .get("url")
            )

            public_path = f"/es-CL/noticias/{item.get('sys', {}).get('id')}" if item.get("sys", {}).get("id") else fields.get("link")

            title = self._clean_text(fields.get("titulo"))
            url = self._absolute_url(public_path)
            img = self._absolute_url(file_url)
            excerpt = self._clean_text(fields.get("descripcion"))
            date_preview = normalizar_fecha(self._clean_text(fields.get("fecha")) or "")

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
