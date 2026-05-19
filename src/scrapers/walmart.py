from datetime import date
from typing import List
from .base import BaseScraper
from schemas import NoticiaSchema
from playwright.sync_api import sync_playwright
import re


class WalmartChileScraper(BaseScraper):
    source = "walmartchile"
    URL = "https://www.walmartchile.cl/category/noticias/"

    def _parse_date(self, date_text: str) -> date | None:
        months = {
            "ene": 1, "feb": 2, "mar": 3, "abr": 4,
            "may": 5, "jun": 6, "jul": 7, "ago": 8,
            "sep": 9, "oct": 10, "nov": 11, "dic": 12,
        }
        parts = re.sub(r'[.,]', '', date_text.lower()).split()
        if len(parts) == 3:
            month_str, day, year = parts
            month = months.get(month_str[:3])
            if month:
                try:
                    return date(int(year), month, int(day))
                except ValueError:
                    pass
        return None

    def fetch(self) -> List[NoticiaSchema]:
        noticias: List[NoticiaSchema] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            page.goto(self.URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_selector("div.card", timeout=20000)

            articles = page.locator("div.card")
            count = articles.count()

            self.logger.info("Noticias encontradas: %s", count)

            for i in range(count):
                art = articles.nth(i)

                # Título — está dentro del h4.card-title > a
                title_el = art.locator("h4.card-title a")
                if title_el.count() == 0:
                    continue
                title = title_el.first.text_content().strip()

                # URL
                url = title_el.first.get_attribute("href")
                if not url:
                    continue

                # Imagen
                img_el = art.locator("img.card-img-top")
                img_url = (
                    img_el.first.get_attribute("src")
                    if img_el.count() else None
                )

                # Fecha — está en p.date con formato "Feb. 10 2026"
                date_el = art.locator("p.date")
                date_preview = None
                if date_el.count():
                    raw_date = date_el.first.text_content().strip()
                    date_preview = self._parse_date(raw_date)

                # Saltar si faltan campos requeridos
                if not img_url or not date_preview:
                    continue

                noticia = NoticiaSchema(
                    title=title,
                    url=url,
                    img=img_url,
                    date_preview=date_preview,
                    source=self.source,
                )
                noticias.append(noticia)

            browser.close()

        return noticias