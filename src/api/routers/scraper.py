from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends

from api.deps import verify_superuser
from models.user import User
from main import procesar_noticias

router = APIRouter(prefix="/scraper", tags=["scraper"])

SuperuserDep = Annotated[User, Depends(verify_superuser)]


@router.post("/run", status_code=200)
async def run_scraper(background_tasks: BackgroundTasks, _: SuperuserDep):
    background_tasks.add_task(procesar_noticias, "api")
    return {"status": "started", "message": "Scraping iniciado en background"}
