from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_session

router = APIRouter(tags=["health"])

SessionDep = Annotated[AsyncSession, Depends(get_async_session)]


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready(session: SessionDep) -> dict[str, str]:
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="Base de datos no disponible")
    return {"status": "ok"}
