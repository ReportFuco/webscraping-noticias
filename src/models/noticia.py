from datetime import date, datetime
from typing import Optional

from sqlalchemy import Column, ForeignKey, Integer
from sqlmodel import Field, SQLModel


class Noticia(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    scrape_run_id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("scraperun.id", ondelete="SET NULL"), index=True, nullable=True),
    )
    title: str
    url: str = Field(unique=True, index=True)
    img: str
    date_preview: str
    source: str
    country: str = Field(default="CL")
    excerpt: Optional[str] = Field(default=None)
    score: int = Field(default=0)
    published_date: Optional[date] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.now)
