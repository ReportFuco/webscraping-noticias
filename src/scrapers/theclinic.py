from playwright.sync_api import sync_playwright
from .base import BaseScraper
from schemas import NoticiaSchema
import re


class TheClinicScraper(BaseScraper):
    source = "theclinic"
    URL = "https://www.theclinic.cl/noticias/negocios/"

    def _extract_date_from_url(self, url: str) -> str | None:
        """Extrae la fecha del URL con formato /YYYY/MM/DD/"""
        match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
        if match:
            year, month, day = match.groups()
            return f"{day}/{month}/{year}"
        return None

    def fetch(self) -> list[NoticiaSchema]:
        noticias: list[NoticiaSchema] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1366, "height": 768},
                locale="es-CL",
                timezone_id="America/Santiago",
            )
            page = context.new_page()
            page.add_init_script("""
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
Object.defineProperty(navigator, 'language', {get: () => 'es-CL'});
Object.defineProperty(navigator, 'languages', {get: () => ['es-CL', 'es', 'en-US', 'en']});
            """)

            page.goto(self.URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(5000)
            page.wait_for_selector("section.listado-seccion article", timeout=30000)

            articles = page.locator("section.listado-seccion article")
            count = articles.count()

            self.logger.info("Noticias encontradas: %s", count)

            for i in range(count):
                art = articles.nth(i)

                # Título — el h2 tiene el link con el title y el texto
                h2 = art.locator("div.titulares h2 a")
                if h2.count() == 0:
                    continue
                title = h2.first.text_content().strip()

                # URL — viene del href del h2 > a (apunta al detalle, tiene la fecha)
                url = h2.first.get_attribute("href")
                if not url:
                    continue

                # Imagen — src del img dentro de div.imagen-post
                img_el = art.locator("div.imagen-post img")
                img_url = (
                    img_el.first.get_attribute("src")
                    if img_el.count() else None
                )

                # Fecha — extraída del propio URL del artículo
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