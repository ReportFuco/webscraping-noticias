from typing import Optional

from sqlmodel import Field, SQLModel


class ScrapeRunSource(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    scrape_run_id: int = Field(foreign_key="scraperun.id", index=True)
    source: str = Field(index=True)
    reviewed_count: int = Field(default=0)
    new_count: int = Field(default=0)
    error_count: int = Field(default=0)
    status: str = Field(default="ok", index=True)
    error_message: Optional[str] = Field(default=None)
