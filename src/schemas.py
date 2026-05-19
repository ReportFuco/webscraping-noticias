from pydantic import BaseModel
from datetime import date


class NoticiaSchema(BaseModel):
    title: str
    url: str
    img: str
    date_preview: date | None
    source: str
    country: str = "CL"
    excerpt: str | None = None
