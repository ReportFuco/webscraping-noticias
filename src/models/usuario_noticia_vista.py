from datetime import datetime
from typing import Optional

from sqlalchemy import Column, ForeignKey, Integer
from sqlmodel import Field, SQLModel


class UsuarioNoticiaVista(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    usuario_id: int = Field(foreign_key="usuario.id", index=True)
    noticia_id: int = Field(
        sa_column=Column(Integer, ForeignKey("noticia.id", ondelete="CASCADE"), index=True, nullable=False),
    )
    visto: bool = Field(default=False)
    enviado_at: datetime = Field(default_factory=datetime.now)
    visto_at: Optional[datetime] = Field(default=None)
    estado: str = Field(default="enviado", index=True)
    detalle: Optional[str] = Field(default=None)
