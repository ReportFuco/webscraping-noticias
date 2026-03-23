from playwright.sync_api import sync_playwright
from .base import BaseScraper
from schemas import NoticiaSchema
from utils import normalizar_fecha
import json


class BioBioScraper(BaseScraper):
    source = "biobiochile"
    URL = "https://www.biobiochile.cl/lista/categorias/nacional"
    MEDIA_BASE_URL = "https://media.biobiochile.cl/wp-content/uploads/"

    def _build_image_url(self, article: dict) -> str | None:
        post_image = article.get("post_image") or {}
        if not isinstance(post_image, dict):
            return None

        thumbnails = post_image.get("thumbnails") or {}
        image_url = (
            thumbnails.get("social", {}).get("URL")
            or thumbnails.get("large", {}).get("URL")
            or post_image.get("URL")
        )
        if not image_url:
            return None

        if image_url.startswith("http://") or image_url.startswith("https://"):
            return image_url

        return f"{self.MEDIA_BASE_URL}{image_url.lstrip('/')}"

    def fetch(self) -> list[NoticiaSchema]:
        noticias: list[NoticiaSchema] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            page.goto(self.URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_selector("body pre", timeout=20000)

            raw_json = page.locator("body pre").text_content()
            data = json.loads(raw_json)
            articles = data.get("articles", [])

            self.logger.info("Noticias encontradas: %s", len(articles))

            for article in articles:
                title = (article.get("post_title") or "").strip()
                url = article.get("post_URL") or article.get("post_URL_https")
                img_url = self._build_image_url(article)
                date_preview = article.get("post_date") or article.get("post_date_txt")

                if not title or not url or not img_url or not date_preview:
                    continue

                noticia = NoticiaSchema(
                    title=title,
                    url=url,
                    img=img_url,
                    date_preview=normalizar_fecha(date_preview),
                    source=self.source,
                )
                noticias.append(noticia)

            browser.close()

        return noticias
