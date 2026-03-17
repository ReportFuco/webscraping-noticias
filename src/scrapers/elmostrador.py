from typing import List
from .base import BaseScraper
from schemas import NoticiaSchema
from playwright.sync_api import sync_playwright
import re


class ElMostradorScraper(BaseScraper):
    source = "elmostrador"
    URL = "https://www.elmostrador.cl/mercados/"

    def _extract_date_from_url(self, url: str) -> str | None:
        """Extrae la fecha del URL con formato /YYYY/MM/DD/"""
        match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
        if match:
            year, month, day = match.groups()
            return f"{day}/{month}/{year}"
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
            page.wait_for_selector("figure.d-main-card", timeout=20000)

            # Selecciona TODAS las noticias (destacada, subdestacadas y listado)
            articles = page.locator("figure.d-main-card")
            count = articles.count()

            print("Noticias encontradas:", count)

            for i in range(count):
                art = articles.nth(i)

                # Título — puede ser h1 o h2 dependiendo del tipo de card
                title_el = art.locator("h1.d-main-card__title a, h2.d-main-card__title a")
                if title_el.count() == 0:
                    continue
                title = title_el.first.text_content().strip()

                # URL
                url = title_el.first.get_attribute("href")
                if not url:
                    continue

                # Imagen
                img_el = art.locator("img.d-main-card__image")
                img_url = None
                if img_el.count():
                    img_src = img_el.first.get_attribute("src")
                    # Si la URL empieza con //, agregar https:
                    if img_src and img_src.startswith("//"):
                        img_url = f"https:{img_src}"
                    else:
                        img_url = img_src

                # Fecha — extraída del URL
                date_preview = self._extract_date_from_url(url)

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