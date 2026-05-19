from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_session
from models.user import User

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    api_key: str = Security(_api_key_header),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    if not api_key:
        raise HTTPException(status_code=401, detail="API key ausente")
    result = await session.execute(
        select(User).where(User.api_key == api_key, User.is_active == True)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="API key inválida")
    return user
