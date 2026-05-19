from typing import Optional

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class ScrapeRunSource(Base):
    __tablename__ = "scraperunsource"

    id: Mapped[int] = mapped_column(primary_key=True)
    scrape_run_id: Mapped[int] = mapped_column(ForeignKey("scraperun.id"), index=True)
    source: Mapped[str] = mapped_column(index=True)
    reviewed_count: Mapped[int] = mapped_column(default=0)
    new_count: Mapped[int] = mapped_column(default=0)
    error_count: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(default="ok", index=True)
    error_message: Mapped[Optional[str]]
