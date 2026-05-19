from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class ScrapeRun(Base):
    __tablename__ = "scraperun"

    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(default=datetime.now, index=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(index=True)
    status: Mapped[str] = mapped_column(default="running", index=True)
    trigger: Mapped[str] = mapped_column(default="manual", index=True)
    total_sources: Mapped[int] = mapped_column(default=0)
    total_reviewed: Mapped[int] = mapped_column(default=0)
    total_new: Mapped[int] = mapped_column(default=0)
    total_errors: Mapped[int] = mapped_column(default=0)
    notes: Mapped[Optional[str]]
