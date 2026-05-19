from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import verify_api_key
from api.schemas import NoticiaPatch, NoticiaResponse, NoticiasQuery, PaginatedNoticias
from database import get_async_session
from models import Noticia

router = APIRouter(prefix="/noticias", tags=["noticias"], dependencies=[Depends(verify_api_key)])

SessionDep = Annotated[AsyncSession, Depends(get_async_session)]
QueryDep = Annotated[NoticiasQuery, Query()]


@router.get("", response_model=PaginatedNoticias)
async def list_noticias(session: SessionDep, q: QueryDep):
    filters = [Noticia.score >= q.score_min]

    optional = [
        (q.source,  lambda: Noticia.source == q.source),
        (q.country, lambda: Noticia.country == q.country),
        (q.desde,   lambda: Noticia.date_preview >= q.desde),
        (q.hasta,   lambda: Noticia.date_preview <= q.hasta),
    ]
    filters += [cond() for val, cond in optional if val is not None]

    if q.buscar:
        pattern = f"%{q.buscar}%"
        filters.append(or_(Noticia.title.ilike(pattern), Noticia.excerpt.ilike(pattern)))

    total = (await session.execute(select(func.count()).select_from(Noticia).where(*filters))).scalar_one()
    items = (
        await session.execute(
            select(Noticia).where(*filters).order_by(Noticia.date_preview.desc()).limit(q.limit).offset(q.offset)
        )
    ).scalars().all()

    return PaginatedNoticias(total=total, limit=q.limit, offset=q.offset, items=list(items))


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
