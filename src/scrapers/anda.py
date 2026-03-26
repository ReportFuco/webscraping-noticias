from __future__ import annotations

import html
import json
import re
from typing import Any, List

import httpx

from .base import BaseScraper
from schemas import NoticiaSchema
from utils import normalizar_fecha


class AndaScraper(BaseScraper):
    source = "anda"
    URL = "https://anda.cl/noticias/"
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
            return f"https://anda.cl{value}"
        return f"https://anda.cl/{value.lstrip('/')}"

    def _extract_meta_content(self, raw_html: str, prop: str) -> str | None:
        match = re.search(
            rf'<meta[^>]+(?:property|name)=["\']{re.escape(prop)}["\'][^>]+content=["\']([^"\']+)["\']',
            raw_html,
            re.IGNORECASE,
        )
        return self._clean_text(match.group(1)) if match else None

    def _extract_listing_items(self, raw_html: str) -> list[dict[str, str | None]]:
        blocks = re.findall(
            r"<article[^>]*class=['\"][^'\"]*anda-card__item[^'\"]*['\"][^>]*>(.*?)</article>",
            raw_html,
            re.IGNORECASE | re.DOTALL,
        )

        items: list[dict[str, str | None]] = []
        seen_urls: set[str] = set()

        for block in blocks:
            url_match = re.search(r'<a[^>]+href=["\'](https?://anda\.cl/[^"\']+)["\']', block, re.IGNORECASE)
            title_match = re.search(
                r'<h3[^>]*class=["\'][^"\']*card__item-title[^"\']*["\'][^>]*>\s*<a[^>]*>(.*?)</a>',
                block,
                re.IGNORECASE | re.DOTALL,
            )
            img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', block, re.IGNORECASE)
            date_match = re.search(
                r'<p[^>]*class=["\'][^"\']*card__item-date[^"\']*["\'][^>]*>(.*?)</p>',
                block,
                re.IGNORECASE | re.DOTALL,
            )
            excerpt_match = re.search(
                r'<p[^>]*class=["\'][^"\']*card__item-excerpt[^"\']*["\'][^>]*>(.*?)</p>',
                block,
                re.IGNORECASE | re.DOTALL,
            )

            url = self._absolute_url(url_match.group(1)) if url_match else None
            title = self._clean_text(title_match.group(1)) if title_match else None
            img = self._absolute_url(self._clean_text(img_match.group(1))) if img_match else None
            date_preview = self._clean_text(date_match.group(1)) if date_match else None
            excerpt = self._clean_text(excerpt_match.group(1)) if excerpt_match else None

            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            items.append(
                {
                    "url": url,
                    "title": title,
                    "img": img,
                    "date_preview": date_preview,
                    "excerpt": excerpt,
                }
            )
            if len(items) >= self.MAX_ARTICLES:
                break

        return items

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
                nodes.extend([item for item in data if isinstance(item, dict)])
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
            date_published = self._clean_text(node.get("datePublished"))
            excerpt = self._clean_text(node.get("description"))

            image_value = node.get("image")
            image_url = None
            if isinstance(image_value, str):
                image_url = image_value
            elif isinstance(image_value, dict):
                image_url = (
                    image_value.get("url")
                    or image_value.get("contentUrl")
                    or image_map.get(str(image_value.get("@id", "")))
                )
            elif isinstance(image_value, list):
                for item in image_value:
                    if isinstance(item, str):
                        image_url = item
                        break
                    if isinstance(item, dict):
                        image_url = (
                            item.get("url")
                            or item.get("contentUrl")
                            or image_map.get(str(item.get("@id", "")))
                        )
                        if image_url:
                            break

            image_url = image_url or self._clean_text(node.get("thumbnailUrl"))

            return {
                "title": title,
                "date_published": date_published,
                "img": self._absolute_url(self._clean_text(image_url)),
                "excerpt": excerpt,
            }

        return {}

    def _parse_article(self, client: httpx.Client, listing_item: dict[str, str | None]) -> NoticiaSchema | None:
        url = listing_item.get("url")
        if not url:
            return None

        response = client.get(url)
        response.raise_for_status()
        raw_html = response.text

        schema_data = self._parse_article_schema(raw_html)

        title = schema_data.get("title") or listing_item.get("title") or self._extract_meta_content(raw_html, "og:title")
        title = self._clean_text(title)
        if title:
            title = re.sub(r"\s*-\s*Anda\s*$", "", title, flags=re.IGNORECASE).strip()

        img = schema_data.get("img") or listing_item.get("img") or self._extract_meta_content(raw_html, "og:image")
        raw_date = schema_data.get("date_published") or self._extract_meta_content(raw_html, "article:published_time") or listing_item.get("date_preview")
        date_preview = normalizar_fecha(raw_date) if raw_date else None
        excerpt = (
            schema_data.get("excerpt")
            or listing_item.get("excerpt")
            or self._extract_meta_content(raw_html, "og:description")
        )

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
            response = client.get(self.URL)
            response.raise_for_status()
            listing_html = response.text

            listing_items = self._extract_listing_items(listing_html)
            self.logger.info("Noticias candidatas ANDA encontradas: %s", len(listing_items))

            for listing_item in listing_items:
                try:
                    noticia = self._parse_article(client, listing_item)
                except Exception as exc:
                    self.logger.warning("No se pudo procesar url=%s error=%s", listing_item.get("url"), exc)
                    continue

                if noticia:
                    noticias.append(noticia)

        return noticias
