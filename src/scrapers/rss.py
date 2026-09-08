"""
Base para las fuentes que publican un RSS usable.

Los medios que se sumaron después (Perú Retail, Expansión, EjePrime) exponen un
feed estándar y su scraper se reducía a las mismas cien líneas de `gestion.py`
con otra URL. Acá está esa lógica una sola vez: un scraper nuevo de RSS debe
poder ser cinco líneas.

`gestion.py` sigue con su implementación propia a propósito: funciona y lleva
369 noticias guardadas; migrarlo es una limpieza aparte, no parte de sumar
fuentes nuevas.
"""
from __future__ import annotations

import re
from datetime import date
from email.utils import parsedate_to_datetime
from typing import List
from xml.etree import ElementTree as ET

import httpx

from .base import BaseScraper
from schemas import NoticiaSchema


NS_CONTENT = "{http://purl.org/rss/1.0/modules/content/}encoded"
IMG_EN_HTML = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)


class RSSScraper(BaseScraper):
    """
    Scraper de un feed RSS 2.0. La subclase solo declara `source`, `country` y
    `URL`; si el feed necesita algo raro, sobreescribe el gancho que toque.
    """

    # Feed a consultar.
    URL: str = ""
    MAX_ITEMS: int = 20
    TIMEOUT: int = 30

    def _xml_limpio(self, crudo: bytes) -> bytes:
        """
        Recorta lo que venga despues del cierre de `</rss>`.

        Cloudflare inyecta su script de challenge al final del feed en varios
        WordPress; el XML sigue siendo valido hasta ahi, pero `ET.fromstring`
        muere con "junk after document element" y la fuente entera devuelve
        cero sin que se note por que. Le pasa hoy a Mercado&Consumo y
        Peru Retail esta detras del mismo Cloudflare.
        """
        cierre = crudo.rfind(b"</rss>")
        return crudo[: cierre + len(b"</rss>")] if cierre != -1 else crudo

    def _parse_fecha(self, valor: str | None) -> date | None:
        """
        `pubDate` viene en RFC 822 ("Mon, 07 Sep 2026 21:46:32 +0000").

        Se parsea con `email.utils` y no con `strptime("%a, %d %b...")` porque
        ese formato depende del locale del proceso: en un servidor con locale
        español, `%b` no reconoce "Sep" y la fuente entera deja de guardar.
        """
        if not valor:
            return None
        try:
            return parsedate_to_datetime(valor.strip()).date()
        except (TypeError, ValueError):
            return None

    def _extraer_imagen(self, item: ET.Element) -> str | None:
        """
        Busca la portada en los tres lugares donde los CMS la dejan.

        Puede devolver None: desde que el pipeline resuelve la `og:image` de la
        nota, una fuente sin imagen en el feed sigue siendo utilizable.
        """
        for hijo in item:
            tag = hijo.tag.lower()
            if tag.endswith(("content", "thumbnail")) and hijo.attrib.get("url"):
                return hijo.attrib["url"]

        enclosure = item.find("enclosure")
        if enclosure is not None and enclosure.attrib.get("url"):
            tipo = enclosure.attrib.get("type", "")
            if not tipo or tipo.startswith("image/"):
                return enclosure.attrib["url"]

        # WordPress mete la foto destacada dentro del cuerpo del item.
        cuerpo = item.findtext(NS_CONTENT)
        if cuerpo:
            match = IMG_EN_HTML.search(cuerpo)
            if match:
                return match.group(1)

        return None

    def _extraer_bajada(self, item: ET.Element) -> str | None:
        """
        La `description` del feed, como respaldo.

        Es solo eso: el pipeline visita la nota igual para sacar la imagen y
        prefiere la `og:description` que encuentre ahí, que en varios de estos
        medios viene sin el "Leer más" ni el aviso de copyright pegados.
        """
        return self._clean_text(item.findtext("description"))

    def fetch(self) -> List[NoticiaSchema]:
        with httpx.Client(
            headers=self.HEADERS, follow_redirects=True, timeout=self.TIMEOUT
        ) as client:
            response = client.get(self.URL)
            response.raise_for_status()
            root = ET.fromstring(self._xml_limpio(response.content))

        noticias: list[NoticiaSchema] = []
        vistas: set[str] = set()

        for item in root.findall("./channel/item"):
            title = self._clean_text(item.findtext("title"))
            url = self._clean_text(item.findtext("link"))
            fecha = self._parse_fecha(item.findtext("pubDate"))

            # Sin título, URL o fecha no hay nada que puntuar ni que ordenar; la
            # imagen sí puede faltar, la resuelve el pipeline.
            if not title or not url or not fecha:
                continue
            if url in vistas:
                continue
            vistas.add(url)

            noticias.append(
                NoticiaSchema(
                    title=title,
                    url=url,
                    img=self._extraer_imagen(item),
                    date_preview=fecha,
                    source=self.source,
                    country=self.country,
                    excerpt=self._extraer_bajada(item),
                )
            )

            if len(noticias) >= self.MAX_ITEMS:
                break

        self.logger.info("Noticias encontradas: %s", len(noticias))
        return noticias
