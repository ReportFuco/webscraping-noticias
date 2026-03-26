from __future__ import annotations

import html
import json
import re
from typing import Any, List

import httpx

from .base import BaseScraper
from schemas import NoticiaSchema
from utils import normalizar_fecha


class CCSScraper(BaseScraper):
    source = "ccs"
    URL = "https://www.ccs.cl/noticias-ccs/"
    MAX_ARTICLES = 10
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    }

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
            return f"https://www.ccs.cl{value}"
        return f"https://www.ccs.cl/{value.lstrip('/')}"

    def _extract_listing_urls(self, raw_html: str) -> list[str]:
        urls: list[str] = []
        seen: set[str] = set()
        pattern = re.compile(
            r'href=["\'](https://www\.ccs\.cl/\d{4}/\d{2}/\d{2}/[^"\']+/?)["\']',
            re.IGNORECASE,
        )

        for match in pattern.finditer(raw_html):
            url = match.group(1).strip()
            if url in seen:
                continue
            seen.add(url)
            urls.append(url)
            if len(urls) >= self.MAX_ARTICLES:
                break

        return urls

    def _extract_meta_content(self, raw_html: str, prop: str) -> str | None:
        match = re.search(
            rf'<meta[^>]+(?:property|name)=["\']{re.escape(prop)}["\'][^>]+content=["\']([^"\']+)["\']',
            raw_html,
            re.IGNORECASE,
        )
        return self._clean_text(match.group(1)) if match else None

    def _parse_article_schema(self, raw_html: str) -> dict[str, str | None]:
        scripts = re.findall(
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            raw_html,
            re.IGNORECASE | re.DOTALL,
        )

        if not scripts:
            return {}

        nodes: list[dict[str, Any]] = []
        image_map: dict[str, str] = {}

        for raw_script in scripts:
            payload = raw_script.strip()
            if not payload:
                continue
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                continue

            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        nodes.append(item)
            elif isinstance(data, dict):
                graph = data.get("@graph")
                if isinstance(graph, list):
                    nodes.extend([item for item in graph if isinstance(item, dict)])
                else:
                    nodes.append(data)

        for node in nodes:
            node_type = node.get("@type")
            is_image = node_type == "ImageObject" or (isinstance(node_type, list) and "ImageObject" in node_type)
            if not is_image:
                continue
            image_id = node.get("@id")
            image_url = node.get("url") or node.get("contentUrl")
            if image_id and image_url:
                image_map[str(image_id)] = str(image_url)

        for node in nodes:
            node_type = node.get("@type")
            is_article = node_type in ("NewsArticle", "Article") or (
                isinstance(node_type, list) and any(t in ("NewsArticle", "Article") for t in node_type)
            )
            if not is_article:
                continue

            title = self._clean_text(node.get("headline") or node.get("name"))
            excerpt = self._clean_text(node.get("description"))
            date_published = self._clean_text(node.get("datePublished"))

            image_value = node.get("image")
            image_url = None
            if isinstance(image_value, str):
                image_url = image_value
            elif isinstance(image_value, dict):
                image_url = image_value.get("url") or image_value.get("contentUrl") or image_map.get(image_value.get("@id", ""))
            elif isinstance(image_value, list):
                for item in image_value:
                    if isinstance(item, str):
                        image_url = item
                        break
                    if isinstance(item, dict):
                        image_url = item.get("url") or item.get("contentUrl") or image_map.get(item.get("@id", ""))
                        if image_url:
                            break

            return {
                "title": title,
                "excerpt": excerpt,
                "date_published": date_published,
                "img": self._absolute_url(self._clean_text(image_url)),
            }

        return {}

    def _parse_article(self, client: httpx.Client, url: str) -> NoticiaSchema | None:
        response = client.get(url)
        response.raise_for_status()
        raw_html = response.text

        schema_data = self._parse_article_schema(raw_html)

        title = schema_data.get("title") or self._extract_meta_content(raw_html, "og:title")
        if title:
            title = re.sub(r"\s*-\s*C[aá]mara de Comercio de Santiago\s*-\s*CCS\s*$", "", title, flags=re.IGNORECASE)
            title = title.strip()

        img = schema_data.get("img") or self._extract_meta_content(raw_html, "og:image")
        raw_date = schema_data.get("date_published") or self._extract_meta_content(raw_html, "article:published_time")
        date_preview = normalizar_fecha(raw_date) if raw_date else None
        excerpt = schema_data.get("excerpt") or self._extract_meta_content(raw_html, "description")

        if not title or not img or not date_preview:
            return None

        return NoticiaSchema(
            title=title,
            url=url,
            img=img,
            date_preview=date_preview,
            source=self.source,
            excerpt=excerpt,
        )

    def fetch(self) -> List[NoticiaSchema]:
        noticias: list[NoticiaSchema] = []

        with httpx.Client(headers=self.HEADERS, follow_redirects=True, timeout=30) as client:
            listing_response = client.get(self.URL)
            listing_response.raise_for_status()
            listing_html = listing_response.text

            article_urls = self._extract_listing_urls(listing_html)
            self.logger.info("Noticias candidatas CCS encontradas: %s", len(article_urls))

            for url in article_urls:
                try:
                    noticia = self._parse_article(client, url)
                except Exception as exc:
                    self.logger.warning("No se pudo procesar url=%s error=%s", url, exc)
                    continue

                if noticia:
                    noticias.append(noticia)

        return noticias
