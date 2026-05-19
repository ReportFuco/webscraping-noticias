from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class Usuario(Base):
    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str]
    whatsapp: Mapped[str] = mapped_column(unique=True, index=True)
    activo: Mapped[bool] = mapped_column(default=True)
