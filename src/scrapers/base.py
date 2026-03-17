from abc import ABC, abstractmethod
from typing import List
from schemas import NoticiaSchema


class BaseScraper(ABC):
    source: str

    @abstractmethod
    def fetch(self) -> List[NoticiaSchema]:
        """
        Debe retornar una lista de noticias normalizadas
        """
        pass
