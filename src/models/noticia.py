from datetime import date, datetime
from typing import Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class Noticia(Base):
    __tablename__ = "noticia"

    id: Mapped[int] = mapped_column(primary_key=True)
    scrape_run_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("scraperun.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str]
    url: Mapped[str] = mapped_column(unique=True, index=True)
    img: Mapped[str]
    date_preview: Mapped[str]
    source: Mapped[str]
    country: Mapped[str] = mapped_column(String, default="CL")
    excerpt: Mapped[Optional[str]]
    score: Mapped[int] = mapped_column(default=0)
    published_date: Mapped[Optional[date]] = mapped_column(index=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
