from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class UsuarioNoticiaVista(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    usuario_id: int = Field(foreign_key="usuario.id", index=True)
    noticia_id: int = Field(foreign_key="noticia.id", index=True)
    visto: bool = Field(default=False)
    enviado_at: datetime = Field(default_factory=datetime.now)
    visto_at: Optional[datetime] = Field(default=None)
    estado: str = Field(default="enviado", index=True)
    detalle: Optional[str] = Field(default=None)
