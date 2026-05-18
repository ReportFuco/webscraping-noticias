from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routers import noticias
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
