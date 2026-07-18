import uuid
from datetime import datetime
from typing import Optional

from fastapi_users_db_sqlalchemy.generics import GUID
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class ApiKey(Base):
    __tablename__ = "api_key"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("api_user.id", ondelete="CASCADE"), index=True)
    name: Mapped[str]
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    key_prefix: Mapped[str] = mapped_column(String(8))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(default=None)
