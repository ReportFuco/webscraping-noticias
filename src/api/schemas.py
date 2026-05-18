from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class NoticiaResponse(BaseModel):
    id: int
    title: str
    url: str
    img: str
    date_preview: str
    source: str
    country: str
    excerpt: str | None
    score: int
    published_date: date | None
    created_at: datetime

    model_config = {"from_attributes": True}


class NoticiaPatch(BaseModel):
    title: str | None = None
    excerpt: str | None = None


class PaginatedNoticias(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[NoticiaResponse]
