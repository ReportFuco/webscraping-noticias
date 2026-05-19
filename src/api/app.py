from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routers import noticias
from api.users import UserCreate, UserRead, UserUpdate, auth_backend, fastapi_users_app
from database import create_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db()
    yield


app = FastAPI(
    title="Noticias API",
    description="API para consultar y enriquecer noticias scrapeadas",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(noticias.router)

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
    fastapi_users_app.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)
