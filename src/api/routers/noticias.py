from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, func, select

from api.schemas import NoticiaPatch, NoticiaResponse, PaginatedNoticias
from database import get_session
from models import Noticia

router = APIRouter(prefix="/noticias", tags=["noticias"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("", response_model=PaginatedNoticias)
def list_noticias(
    session: SessionDep,
    source: str | None = Query(default=None),
    country: str | None = Query(default=None),
    score_min: int = Query(default=0, ge=0),
    # Filtros por fecha de publicación (published_date)
    desde: date | None = Query(default=None, description="Fecha publicación desde (YYYY-MM-DD)"),
    hasta: date | None = Query(default=None, description="Fecha publicación hasta (YYYY-MM-DD)"),
    # Filtros por fecha de ingesta (created_at)
    ingresado_desde: date | None = Query(default=None, description="Fecha ingesta desde (YYYY-MM-DD)"),
    ingresado_hasta: date | None = Query(default=None, description="Fecha ingesta hasta (YYYY-MM-DD)"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    filters = [Noticia.score >= score_min]

    if source:
        filters.append(Noticia.source == source)
    if country:
        filters.append(Noticia.country == country)
    if desde:
        filters.append(Noticia.published_date >= desde)
    if hasta:
        filters.append(Noticia.published_date <= hasta)
    if ingresado_desde:
        filters.append(func.date(Noticia.created_at) >= ingresado_desde)
    if ingresado_hasta:
        filters.append(func.date(Noticia.created_at) <= ingresado_hasta)

    total = session.exec(select(func.count()).select_from(Noticia).where(*filters)).one()
    items = session.exec(
        select(Noticia).where(*filters).order_by(Noticia.created_at.desc()).limit(limit).offset(offset)
    ).all()

    return PaginatedNoticias(total=total, limit=limit, offset=offset, items=list(items))


@router.get("/{noticia_id}", response_model=NoticiaResponse)
def get_noticia(noticia_id: int, session: SessionDep):
    noticia = session.get(Noticia, noticia_id)
    if not noticia:
        raise HTTPException(status_code=404, detail="Noticia no encontrada")
    return noticia


@router.patch("/{noticia_id}", response_model=NoticiaResponse)
def patch_noticia(noticia_id: int, body: NoticiaPatch, session: SessionDep):
    noticia = session.get(Noticia, noticia_id)
    if not noticia:
        raise HTTPException(status_code=404, detail="Noticia no encontrada")

    if body.title is not None:
        noticia.title = body.title
    if body.excerpt is not None:
        noticia.excerpt = body.excerpt

    session.add(noticia)
    session.commit()
    session.refresh(noticia)
    return noticia
