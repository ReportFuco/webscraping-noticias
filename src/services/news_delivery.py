from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Iterable

from sqlmodel import Session, select

import config as ENV
from models import Noticia, Usuario, UsuarioNoticiaVista
from utils import BotWhatsApp


LOGGER = logging.getLogger(__name__)
MAX_NEWS_AGE_DAYS = 4


def _build_message(usuario: Usuario, noticias: Iterable[Noticia]) -> str:
    noticias = list(noticias)
    saludo = f"Hola {usuario.nombre}, aquí van tus noticias nuevas:"

    bloques: list[str] = [saludo]
    for idx, noticia in enumerate(noticias, start=1):
        excerpt = (noticia.excerpt or "").strip()
        excerpt_line = f" — {excerpt}" if excerpt else ""
        fecha = f" | {noticia.date_preview}" if noticia.date_preview else ""
        bloques.append(
            f"{idx}. {noticia.title} ({noticia.source}{fecha}){excerpt_line}\n{noticia.url}"
        )

    return "\n\n".join(bloques)


def _parse_news_date(noticia: Noticia) -> datetime | None:
    if not noticia.date_preview:
        return None
    try:
        return datetime.strptime(noticia.date_preview, "%d/%m/%Y")
    except ValueError:
        return None


def registrar_huella_no_enviada(
    session: Session,
    usuario_id: int,
    noticias: Iterable[Noticia],
    estado: str,
    detalle: str | None = None,
) -> int:
    count = 0
    for noticia in noticias:
        session.add(
            UsuarioNoticiaVista(
                usuario_id=usuario_id,
                noticia_id=noticia.id,
                visto=True,
                visto_at=datetime.now(),
                estado=estado,
                detalle=detalle,
            )
        )
        count += 1
    session.commit()
    return count


def obtener_noticias_no_enviadas(session: Session, usuario_id: int, limit: int = 10) -> list[Noticia]:
    sent_ids = set(
        session.exec(
            select(UsuarioNoticiaVista.noticia_id).where(UsuarioNoticiaVista.usuario_id == usuario_id)
        ).all()
    )

    statement = select(Noticia).order_by(Noticia.created_at.desc())
    noticias = session.exec(statement).all()
    pendientes = [noticia for noticia in noticias if noticia.id not in sent_ids]

    cutoff = datetime.now() - timedelta(days=MAX_NEWS_AGE_DAYS)
    vencidas: list[Noticia] = []
    recientes: list[Noticia] = []

    for noticia in pendientes:
        noticia_dt = _parse_news_date(noticia)
        if noticia_dt is not None and noticia_dt < cutoff:
            vencidas.append(noticia)
        else:
            recientes.append(noticia)

    if vencidas:
        marcadas = registrar_huella_no_enviada(
            session,
            usuario_id,
            vencidas,
            estado="omitida_antigua",
            detalle=f"No enviada por antigüedad > {MAX_NEWS_AGE_DAYS} días",
        )
        LOGGER.info(
            "Marcadas como omitidas por antigüedad usuario_id=%s cantidad=%s",
            usuario_id,
            marcadas,
        )

    return recientes[:limit]


def registrar_envio(session: Session, usuario_id: int, noticias: Iterable[Noticia]) -> None:
    for noticia in noticias:
        session.add(
            UsuarioNoticiaVista(
                usuario_id=usuario_id,
                noticia_id=noticia.id,
                visto=False,
                estado="enviado",
            )
        )
    session.commit()


def enviar_noticias_pendientes(session: Session, limit_por_usuario: int = 10) -> dict[str, object]:
    bot = BotWhatsApp(**ENV.EVOLUTION_CREDENCIALS)
    usuarios = session.exec(select(Usuario).where(Usuario.activo == True)).all()

    resultado: dict[str, object] = {"usuarios": [], "total_envios": 0}

    if not usuarios:
        LOGGER.warning("No hay usuarios activos en la base de datos para enviar noticias")
        resultado["warning"] = "sin_usuarios_activos"
        return resultado

    for usuario in usuarios:
        noticias = obtener_noticias_no_enviadas(session, usuario.id, limit_por_usuario)
        if not noticias:
            LOGGER.info("Sin noticias nuevas para usuario=%s", usuario.whatsapp)
            resultado["usuarios"].append(
                {"usuario": usuario.nombre, "numero": usuario.whatsapp, "enviadas": 0, "status": "sin_novedades"}
            )
            continue

        mensaje = _build_message(usuario, noticias)
        response = bot.enviar_mensaje(usuario.whatsapp, mensaje, delay=1200)
        ok = bool(response.get("ok"))

        if ok:
            registrar_envio(session, usuario.id, noticias)
            resultado["total_envios"] = int(resultado["total_envios"]) + len(noticias)

        resultado["usuarios"].append(
            {
                "usuario": usuario.nombre,
                "numero": usuario.whatsapp,
                "enviadas": len(noticias) if ok else 0,
                "status": "ok" if ok else "error",
                "response": response,
            }
        )

    return resultado
