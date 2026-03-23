from .base import BaseScraper
from playwright.sync_api import sync_playwright
from typing import List, Optional
from schemas import NoticiaSchema
from utils import normalizar_fecha
import re


class MeganoticiasScraper(BaseScraper):
    source = "Meganoticias"
    url = "https://www.meganoticias.cl/nacional/"

    def _extract_date_from_url(self, url: str) -> Optional[str]:
        """Extrae la fecha del URL con formato DD-MM-YYYY al final"""
        match = re.search(r'(\d{2})-(\d{2})-(\d{4})\.html$', url)
        if match:
            day, month, year = match.groups()
            return f"{day}/{month}/{year}"
        return None

    def fetch(self) -> List[NoticiaSchema]:
        noticias: List[NoticiaSchema] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            page.goto(self.url)
            page.wait_for_selector("div.box-notas article.box-generica")

            articles = page.locator("div.box-notas article.box-generica")
            count = articles.count()

            self.logger.info("Noticias encontradas: %s", count)

            for i in range(count):
                art = articles.nth(i)

                # Título
                h2 = art.locator("h2")
                if h2.count() == 0:
                    continue
                title = h2.first.text_content().strip()

                # URL
                link = art.locator("a[href]")
                url = link.first.get_attribute("href") if link.count() else None
                if not url:
                    continue

                # Imagen
                img = art.locator("img")
                img_url = (
                    img.first.get_attribute("src")
                    or img.first.get_attribute("data-src")
                    if img.count() else None
                )

                # Fecha — Prioridad 1: extraer del URL
                date_preview = self._extract_date_from_url(url)
                
                # Fecha — Prioridad 2: si no está en URL, usar el texto y normalizar
                if not date_preview:
                    fecha_el = art.locator(".fecha p")
                    if fecha_el.count():
                        datetime_attr = fecha_el.first.get_attribute("datetime")
                        raw_date = datetime_attr or fecha_el.first.text_content().strip()
                        date_preview = normalizar_fecha(raw_date)

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