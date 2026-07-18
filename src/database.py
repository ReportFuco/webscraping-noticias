from pathlib import Path
from typing import AsyncGenerator

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session

from config import DATABASE_HOST, DATABASE_NAME, DATABASE_PASSWORD, DATABASE_PORT, DATABASE_USER

DATABASE_URL = f"postgresql://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"
ASYNC_DATABASE_URL = f"postgresql+asyncpg://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"

engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True, pool_recycle=1800)
async_engine = create_async_engine(ASYNC_DATABASE_URL, echo=False, pool_pre_ping=True, pool_recycle=1800)
_async_session_maker = async_sessionmaker(async_engine, expire_on_commit=False)

_BASE_DIR = Path(__file__).resolve().parent.parent


def create_db() -> None:
    """Aplica todas las migraciones pendientes vía Alembic."""
    cfg = Config(str(_BASE_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
    command.upgrade(cfg, "head")


def get_session():
    with Session(engine) as session:
        yield session


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with _async_session_maker() as session:
        yield session
