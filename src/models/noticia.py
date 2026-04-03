from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional


class Noticia(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    scrape_run_id: Optional[int] = Field(default=None, foreign_key="scraperun.id", index=True)
    title: str
    url: str = Field(unique=True, index=True)
    img: str
    date_preview: str
    source: str
    excerpt: Optional[str] = Field(default=None)
    score: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.now)
