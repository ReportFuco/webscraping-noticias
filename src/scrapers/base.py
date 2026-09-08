import html
import logging
import re
from abc import ABC, abstractmethod
from typing import List
from schemas import NoticiaSchema


class BaseScraper(ABC):
    source: str
    country: str = "CL"

    # Raíz del sitio. `_absolute_url` la usa para resolver rutas relativas, así
    # que debe estar definida en cualquier scraper que la llame.
    BASE_URL: str = ""

    HEADERS: dict[str, str] = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    }

    @property
    def logger(self) -> logging.Logger:
        return logging.getLogger(f"scraper.{self.source}")

    def _clean_text(self, value: str | None) -> str | None:
        """
        Deja texto plano: resuelve entidades HTML, quita etiquetas y colapsa
        espacios. Devuelve None si no queda nada.
        """
        if not value:
            return None
        text = html.unescape(value)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text or None

    def _absolute_url(self, value: str | None) -> str | None:
        """
        Resuelve `value` contra `BASE_URL`. Acepta URLs absolutas (las devuelve
        tal cual), protocol-relative (`//host/...`) y rutas relativas.
        """
        if not value:
            return None
        if value.startswith(("http://", "https://")):
            return value
        if value.startswith("//"):
            return f"https:{value}"
        if value.startswith("/"):
            return f"{self.BASE_URL}{value}"
        return f"{self.BASE_URL}/{value.lstrip('/')}"

    @abstractmethod
    def fetch(self) -> List[NoticiaSchema]:
        """
        Debe retornar una lista de noticias normalizadas
        """
        pass
