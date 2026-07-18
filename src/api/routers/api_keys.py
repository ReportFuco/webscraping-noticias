from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import hash_api_key
from api.schemas import ApiKeyCreate, ApiKeyCreateResponse, ApiKeyResponse
from api.users import current_active_user
from database import get_async_session
from models.api_key import ApiKey
from models.user import User

router = APIRouter(prefix="/me/api-keys", tags=["api-keys"])

SessionDep = Annotated[AsyncSession, Depends(get_async_session)]
UserDep = Annotated[User, Depends(current_active_user)]


@router.get("", response_model=list[ApiKeyResponse])
async def list_api_keys(session: SessionDep, user: UserDep):
    result = await session.execute(
        select(ApiKey).where(ApiKey.user_id == user.id).order_by(ApiKey.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=ApiKeyCreateResponse, status_code=201)
async def create_api_key(body: ApiKeyCreate, session: SessionDep, user: UserDep):
    raw_key = secrets.token_urlsafe(32)
    api_key = ApiKey(
        user_id=user.id,
        name=body.name,
        key_hash=hash_api_key(raw_key),
        key_prefix=raw_key[:8],
    )
    session.add(api_key)
    await session.commit()
    await session.refresh(api_key)

    # api_key en claro: única vez que se muestra, no se puede recuperar después.
    return ApiKeyCreateResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        api_key=raw_key,
    )


@router.delete("/{api_key_id}", status_code=204)
async def revoke_api_key(api_key_id: int, session: SessionDep, user: UserDep):
    api_key = await session.get(ApiKey, api_key_id)
    if not api_key or api_key.user_id != user.id:
        raise HTTPException(status_code=404, detail="API key no encontrada")
    api_key.is_active = False
    session.add(api_key)
    await session.commit()
