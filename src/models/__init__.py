# Debe importarse antes que fastapi_users_db_sqlalchemy (vía .api_key más abajo):
# hay un import circular en fastapi_users_db_sqlalchemy==7.0.0 que, si su submódulo
# .generics se importa primero, deja fastapi_users.db.SQLAlchemyBaseUserTableUUID
# roto (ImportError silenciado) por el resto del proceso.
import fastapi_users.db  # noqa: F401

from .api_key import ApiKey
from .noticia import Noticia
from .scrape_run import ScrapeRun
from .scrape_run_source import ScrapeRunSource
from .usuario import Usuario
from .usuario_noticia_vista import UsuarioNoticiaVista
from .webhook import WebhookSubscriptor


__all__ = [
    "ApiKey", "Noticia", "ScrapeRun", "ScrapeRunSource", "Usuario", "UsuarioNoticiaVista",
    "WebhookSubscriptor",
]
