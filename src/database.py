from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlmodel import Session, create_engine

from config import DATABASE_HOST, DATABASE_NAME, DATABASE_PASSWORD, DATABASE_PORT, DATABASE_USER

DATABASE_URL = f"postgresql://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"

engine = create_engine(DATABASE_URL, echo=False)

_BASE_DIR = Path(__file__).resolve().parent.parent


def create_db() -> None:
    """Aplica todas las migraciones pendientes vía Alembic."""
    cfg = Config(str(_BASE_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
    command.upgrade(cfg, "head")


def get_session():
    with Session(engine) as session:
        yield session
