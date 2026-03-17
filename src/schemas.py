from pydantic import BaseModel
from datetime import datetime


class NoticiaSchema(BaseModel):
    title: str
    url: str
    img: str
    date_preview: datetime | str
    source: str