from typing import List
from .base import BaseScraper
from schemas import NoticiaSchema
from playwright.sync_api import sync_playwright
from utils import normalizar_fecha


class PortalInnovaScraper(BaseScraper):
    source = "portalinnova"
    URL = "https://portalinnova.cl/noticias-economia-y-negocios/"

    def fetch(self) -> List[NoticiaSchema]:
        noticias: List[NoticiaSchema] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            page.goto(self.URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_selector("div.td_module_2", timeout=20000)

            articles = page.locator("div.td_module_2")
            count = articles.count()

            self.logger.info("Noticias encontradas: %s", count)

            for i in range(count):
                art = articles.nth(i)

                # Título — priorizar atributo title, fallback a text_content
                title_el = art.locator("h3.entry-title a")
                if title_el.count() == 0:
                    continue
                
                # Intentar primero el atributo title (título completo)
                title = title_el.first.get_attribute("title")
                # Si no hay title, usar el texto visible
                if not title:
                    title = title_el.first.text_content().strip()

                # URL
                url = title_el.first.get_attribute("href")
                if not url:
                    continue

                # Imagen
                img_el = art.locator("img.entry-thumb")
                img_url = (
                    img_el.first.get_attribute("src")
                    if img_el.count() else None
                )

                # Fecha
                fecha_el = art.locator("time.entry-date")
                date_preview = None
                if fecha_el.count():
                    datetime_attr = fecha_el.first.get_attribute("datetime")
                    if datetime_attr:
                        date_preview = normalizar_fecha(datetime_attr)
                    else:
                        raw_date = fecha_el.first.text_content().strip()
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