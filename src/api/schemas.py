from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class NoticiaResponse(BaseModel):
    id: int
    title: str
    url: str
    img: str
    date_preview: date | None
    source: str
    country: str
    excerpt: str | None
    score: int
    created_at: datetime

    model_config = {"from_attributes": True}


class NoticiasQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str | None = None
    country: str | None = None
    score_min: int = Field(default=0, ge=0)
    desde: date | None = Field(default=None, description="Fecha publicación desde (YYYY-MM-DD)")
    hasta: date | None = Field(default=None, description="Fecha publicación hasta (YYYY-MM-DD)")
    buscar: str | None = Field(default=None, description="Búsqueda de texto en título y bajada")
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class NoticiaPatch(BaseModel):
    title: str | None = None
    excerpt: str | None = None


class PaginatedNoticias(BaseModel):
    total: int
    limit: int
    offset: int
    items: Sequence[NoticiaResponse]


class WebhookCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    url: str = Field(min_length=10)
    secret: str = Field(min_length=8)

    model_config = ConfigDict(extra="forbid")


class WebhookUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    url: str | None = Field(default=None, min_length=10)
    secret: str | None = Field(default=None, min_length=8)
    is_active: bool | None = None

    model_config = ConfigDict(extra="forbid")


class WebhookResponse(BaseModel):
    id: int
    name: str
    url: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    model_config = ConfigDict(extra="forbid")


class ApiKeyResponse(BaseModel):
    id: int
    name: str
    key_prefix: str
    is_active: bool
    created_at: datetime
    last_used_at: datetime | None

    model_config = {"from_attributes": True}


class ApiKeyCreateResponse(ApiKeyResponse):
    api_key: str
