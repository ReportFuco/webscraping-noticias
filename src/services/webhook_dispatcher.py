from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.noticia import Noticia
from models.webhook import WebhookSubscriptor

LOGGER = logging.getLogger(__name__)


def _build_payload(scrape_run_id: int, noticias: list[Noticia]) -> dict[str, Any]:
    return {
        "event": "scrape_completed",
        "scrape_run_id": scrape_run_id,
        "total_new": len(noticias),
        "noticias": [
            {
                "id": n.id,
                "title": n.title,
                "url": n.url,
                "img": n.img,
                "date_preview": n.date_preview.isoformat() if n.date_preview else None,
                "source": n.source,
                "country": n.country,
                "excerpt": n.excerpt,
                "score": n.score,
            }
            for n in noticias
        ],
    }


async def _fire_one(
    client: httpx.AsyncClient,
    sub: WebhookSubscriptor,
    payload: dict[str, Any],
) -> None:
    try:
        r = await client.post(
            sub.url,
            json=payload,
            headers={"X-Webhook-Secret": sub.secret},
            timeout=10,
        )
        LOGGER.info("Webhook enviado name=%s status=%s", sub.name, r.status_code)
    except Exception as exc:
        LOGGER.warning("Webhook falló name=%s url=%s error=%s", sub.name, sub.url, exc)


async def _dispatch_all(
    subs: list[WebhookSubscriptor],
    payload: dict[str, Any],
) -> None:
    async with httpx.AsyncClient() as client:
        await asyncio.gather(*[_fire_one(client, s, payload) for s in subs])


def dispatch_webhooks(session: Session, scrape_run_id: int, noticias: list[Noticia]) -> None:
    subs = session.execute(
        select(WebhookSubscriptor).where(WebhookSubscriptor.is_active == True)
    ).scalars().all()

    if not subs:
        return

    payload = _build_payload(scrape_run_id, noticias)
    asyncio.run(_dispatch_all(list(subs), payload))
    LOGGER.info("Webhooks disparados subscriptores=%s noticias=%s", len(subs), len(noticias))
