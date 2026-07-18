import os
from pathlib import Path

from fastapi import FastAPI

from api.routers import api_keys, health, noticias, scraper, webhooks
from api.users import UserCreate, UserRead, UserUpdate, auth_backend, fastapi_users_app
from utils import setup_logging

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_LOG_FILE = BASE_DIR / "logs" / "api.log"

# Archivo dedicado en vez de depender de la captura de stdout/stderr de gunicorn
# (esa redirección no estaba entregando los logs de la app, ver docs/auditoria).
setup_logging(log_level=os.getenv("LOG_LEVEL", "INFO"), log_file=os.getenv("API_LOG_FILE", str(DEFAULT_LOG_FILE)))

# Las migraciones (alembic upgrade head) corren como paso de deploy
# (ExecStartPre en noticias-api.service), no en el arranque de la app,
# para evitar que cada worker de gunicorn las dispare en paralelo.
app = FastAPI(
    title="Noticias API",
    description="API para consultar y enriquecer noticias scrapeadas",
    version="1.0.0",
)

app.include_router(health.router)
app.include_router(api_keys.router)
app.include_router(noticias.router)
app.include_router(scraper.router)
app.include_router(webhooks.router)

app.include_router(
    fastapi_users_app.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)
app.include_router(
    fastapi_users_app.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users_app.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users_app.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)
