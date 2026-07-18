from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class WebhookSubscriptor(Base):
    __tablename__ = "webhook_subscriptor"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    url: Mapped[str]
    secret: Mapped[str]
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
