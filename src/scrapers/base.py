import logging
from abc import ABC, abstractmethod
from typing import List
from schemas import NoticiaSchema


class BaseScraper(ABC):
    source: str

    @property
    def logger(self) -> logging.Logger:
        return logging.getLogger(f"scraper.{self.source}")

    @abstractmethod
    def fetch(self) -> List[NoticiaSchema]:
        """
        Debe retornar una lista de noticias normalizadas
        """
        pass
