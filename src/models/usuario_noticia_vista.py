from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class UsuarioNoticiaVista(Base):
    __tablename__ = "usuarionoticiavista"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"), index=True)
    noticia_id: Mapped[int] = mapped_column(
        ForeignKey("noticia.id", ondelete="CASCADE"), index=True
    )
    visto: Mapped[bool] = mapped_column(default=False)
    enviado_at: Mapped[datetime] = mapped_column(default=datetime.now)
    visto_at: Mapped[Optional[datetime]]
    estado: Mapped[str] = mapped_column(default="enviado", index=True)
    detalle: Mapped[Optional[str]]
