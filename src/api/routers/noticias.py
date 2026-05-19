from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import verify_api_key
from api.schemas import NoticiaPatch, NoticiaResponse, PaginatedNoticias
from database import get_async_session
from models import Noticia

router = APIRouter(prefix="/noticias", tags=["noticias"], dependencies=[Depends(verify_api_key)])

SessionDep = Annotated[AsyncSession, Depends(get_async_session)]


@router.get("", response_model=PaginatedNoticias)
async def list_noticias(
    session: SessionDep,
    source: str | None = Query(default=None),
    country: str | None = Query(default=None),
    score_min: int = Query(default=0, ge=0),
    desde: date | None = Query(default=None, description="Fecha publicación desde (YYYY-MM-DD)"),
    hasta: date | None = Query(default=None, description="Fecha publicación hasta (YYYY-MM-DD)"),
    buscar: str | None = Query(default=None, description="Búsqueda de texto en título y bajada"),
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
    if buscar:
        pattern = f"%{buscar}%"
        filters.append(or_(Noticia.title.ilike(pattern), Noticia.excerpt.ilike(pattern)))

    total = (await session.execute(select(func.count()).select_from(Noticia).where(*filters))).scalar_one()
    items = (
        await session.execute(
            select(Noticia).where(*filters).order_by(Noticia.published_date.desc()).limit(limit).offset(offset)
        )
    ).scalars().all()

    return PaginatedNoticias(total=total, limit=limit, offset=offset, items=list(items))


@router.get("/{noticia_id}", response_model=NoticiaResponse)
async def get_noticia(noticia_id: int, session: SessionDep):
    noticia = await session.get(Noticia, noticia_id)
    if not noticia:
        raise HTTPException(status_code=404, detail="Noticia no encontrada")
    return noticia


@router.patch("/{noticia_id}", response_model=NoticiaResponse)
async def patch_noticia(noticia_id: int, body: NoticiaPatch, session: SessionDep):
    noticia = await session.get(Noticia, noticia_id)
    if not noticia:
        raise HTTPException(status_code=404, detail="Noticia no encontrada")

    if body.title is not None:
        noticia.title = body.title
    if body.excerpt is not None:
        noticia.excerpt = body.excerpt

    session.add(noticia)
    await session.commit()
    await session.refresh(noticia)
    return noticia
