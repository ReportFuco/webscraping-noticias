import secrets

from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy import Column, String

from models.base import Base


class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "api_user"

    api_key = Column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
        default=lambda: secrets.token_urlsafe(32),
    )
