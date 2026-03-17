from typing import List
from .base import BaseScraper
from schemas import NoticiaSchema
from playwright.sync_api import sync_playwright
from utils import normalizar_fecha


class PublimetroScraper(BaseScraper):
    source = "publimetro"
    URL = "https://www.publimetro.cl/noticias/"

    def fetch(self) -> List[NoticiaSchema]:
        noticias: List[NoticiaSchema] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            page.goto(self.URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_selector("div.b-results-list", timeout=20000)

            # Selecciona todos los contenedores de noticias
            articles = page.locator("div.b-results-list")
            count = articles.count()

            print("Noticias encontradas:", count)

            for i in range(count):
                art = articles.nth(i)

                # Título — está en h2.c-heading > a
                title_el = art.locator("h2.c-heading a")
                if title_el.count() == 0:
                    continue
                title = title_el.first.text_content().strip()

                # URL
                url = title_el.first.get_attribute("href")
                if not url:
                    continue
                
                # Completar URL si es relativa
                if url.startswith("/"):
                    url = f"https://www.publimetro.cl{url}"

                # Imagen — está en figure.c-media-item img
                img_el = art.locator("figure.c-media-item img")
                img_url = None
                if img_el.count():
                    # Intentar src primero, luego srcset
                    img_url = img_el.first.get_attribute("src")
                    if not img_url or "data:image" in img_url:
                        # Si es lazy loading, buscar en srcset
                        srcset = img_el.first.get_attribute("srcset")
                        if srcset:
                            # Tomar la primera URL del srcset
                            img_url = srcset.split(",")[0].strip().split()[0]

                # Fecha — está en time.c-date con atributo datetime
                fecha_el = art.locator("time.c-date")
                date_preview = None
                if fecha_el.count():
                    datetime_attr = fecha_el.first.get_attribute("datetime")
                    if datetime_attr:
                        date_preview = normalizar_fecha(datetime_attr)
                    else:
                        # Fallback: texto visible
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