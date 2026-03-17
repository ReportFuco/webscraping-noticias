from playwright.sync_api import sync_playwright
from .base import BaseScraper
from schemas import NoticiaSchema
from utils import normalizar_fecha 
import re


class BioBioScraper(BaseScraper):
    source = "biobiochile"
    URL = "https://www.biobiochile.cl/lista/categorias/nacional"

    def fetch(self) -> list[NoticiaSchema]:
        noticias: list[NoticiaSchema] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            # wait_until="domcontentloaded" no espera JS ni recursos externos
            page.goto(self.URL, wait_until="domcontentloaded", timeout=60000)

            page.wait_for_selector("div.results article", timeout=20000)

            articles = page.locator("div.results article")
            count = articles.count()

            print("Noticias encontradas:", count)

            for i in range(count):
                art = articles.nth(i)

                # Título
                h2 = art.locator("h2.article-title")
                if h2.count() == 0:
                    continue
                title = h2.first.text_content().strip()

                # URL
                link = art.locator("a[href]")
                if link.count() == 0:
                    continue
                url = link.first.get_attribute("href")

                # Imagen
                img_div = art.locator("div.article-image")
                img_url = None
                if img_div.count():
                    style = img_div.first.get_attribute("style") or ""
                    match = re.search(r'url\(["\']?(.*?)["\']?\)', style)
                    if match:
                        img_url = match.group(1)

                # Fecha
                fecha_el = art.locator("div.article-date-hour")
                date_preview = (
                    fecha_el.first.text_content().strip()
                    if fecha_el.count() else None
                )

                if not url or not img_url or not date_preview:
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