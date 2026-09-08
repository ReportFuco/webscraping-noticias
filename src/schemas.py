from pydantic import BaseModel
from datetime import date


class NoticiaSchema(BaseModel):
    title: str
    url: str
    # Opcional porque hay feeds RSS que no traen imagen (Peru Retail,
    # Expansion, EjePrime). El pipeline la completa con la og:image de la
    # nota; si tampoco hay, la descarta antes de guardarla, asi que la
    # columna `noticia.img` sigue siendo NOT NULL.
    img: str | None = None
    date_preview: date | None
    source: str
    country: str = "CL"
    excerpt: str | None = None
