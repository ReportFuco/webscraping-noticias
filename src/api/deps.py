import hashlib
from datetime import datetime

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_session
from models.api_key import ApiKey
from models.user import User

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


async def verify_api_key(
    api_key: str = Security(_api_key_header),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    if not api_key:
        raise HTTPException(status_code=401, detail="API key ausente")

    result = await session.execute(
        select(ApiKey, User)
        .join(User, ApiKey.user_id == User.id)
        .where(ApiKey.key_hash == hash_api_key(api_key), ApiKey.is_active == True, User.is_active == True)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=401, detail="API key inválida")

    api_key_row, user = row
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Cuenta no verificada. Verifica tu email antes de usar la API.")

    await session.execute(update(ApiKey).where(ApiKey.id == api_key_row.id).values(last_used_at=datetime.now()))
    await session.commit()

    return user


async def verify_superuser(user: User = Depends(verify_api_key)) -> User:
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Se requiere superuser")
    return user
