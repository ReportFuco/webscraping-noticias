from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class ScrapeRun(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    started_at: datetime = Field(default_factory=datetime.now, index=True)
    finished_at: Optional[datetime] = Field(default=None, index=True)
    status: str = Field(default="running", index=True)
    trigger: str = Field(default="manual", index=True)
    total_sources: int = Field(default=0)
    total_reviewed: int = Field(default=0)
    total_new: int = Field(default=0)
    total_errors: int = Field(default=0)
    notes: Optional[str] = Field(default=None)
