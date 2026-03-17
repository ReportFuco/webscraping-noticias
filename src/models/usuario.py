from sqlmodel import SQLModel, Field
from typing import Optional


class Usuario(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    whatsapp: str = Field(unique=True, index=True)
    activo: bool = Field(default=True)