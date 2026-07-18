from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import verify_superuser
from database import get_async_session
from api.schemas import WebhookCreate, WebhookResponse, WebhookUpdate
from models.user import User
from models.webhook import WebhookSubscriptor

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

SessionDep = Annotated[AsyncSession, Depends(get_async_session)]
SuperuserDep = Annotated[User, Depends(verify_superuser)]


@router.get("", response_model=list[WebhookResponse])
async def list_webhooks(session: SessionDep, _: SuperuserDep):
    result = await session.execute(select(WebhookSubscriptor).order_by(WebhookSubscriptor.id))
    return result.scalars().all()


@router.post("", response_model=WebhookResponse, status_code=201)
async def create_webhook(body: WebhookCreate, session: SessionDep, _: SuperuserDep):
    webhook = WebhookSubscriptor(**body.model_dump())
    session.add(webhook)
    await session.commit()
    await session.refresh(webhook)
    return webhook


@router.patch("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(webhook_id: int, body: WebhookUpdate, session: SessionDep, _: SuperuserDep):
    webhook = await session.get(WebhookSubscriptor, webhook_id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook no encontrado")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(webhook, field, value)
    await session.commit()
    await session.refresh(webhook)
    return webhook


@router.delete("/{webhook_id}", status_code=204)
async def delete_webhook(webhook_id: int, session: SessionDep, _: SuperuserDep):
    webhook = await session.get(WebhookSubscriptor, webhook_id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook no encontrado")
    await session.delete(webhook)
    await session.commit()
