from __future__ import annotations

import logging
from typing import Iterable

from sqlmodel import Session, select

import config as ENV
from models import Noticia, Usuario, UsuarioNoticiaVista
from utils import BotWhatsApp


LOGGER = logging.getLogger(__name__)

DEFAULT_RECIPIENTS = [
    {"nombre": "Pancho", "whatsapp": "56978086719"},
    {"nombre": "Gonzalo", "whatsapp": "56942099844"},
]


def asegurar_usuarios_base(session: Session) -> None:
    for recipient in DEFAULT_RECIPIENTS:
        existing = session.exec(
            select(Usuario).where(Usuario.whatsapp == recipient["whatsapp"])
        ).first()
        if existing:
            if existing.nombre != recipient["nombre"]:
                existing.nombre = recipient["nombre"]
                session.add(existing)
            continue

        session.add(Usuario(nombre=recipient["nombre"], whatsapp=recipient["whatsapp"], activo=True))

    session.commit()


def _build_message(usuario: Usuario, noticias: Iterable[Noticia]) -> str:
    noticias = list(noticias)
    saludo = f"Hola {usuario.nombre}, aquí van tus noticias nuevas:"

    bloques: list[str] = [saludo]
    for idx, noticia in enumerate(noticias, start=1):
        excerpt = (noticia.excerpt or "").strip()
        excerpt_line = f" — {excerpt}" if excerpt else ""
        bloques.append(
            f"{idx}. {noticia.title} ({noticia.source}){excerpt_line}\n{noticia.url}"
        )

    return "\n\n".join(bloques)


def obtener_noticias_no_enviadas(session: Session, usuario_id: int, limit: int = 5) -> list[Noticia]:
    sent_ids = set(
        session.exec(
            select(UsuarioNoticiaVista.noticia_id).where(UsuarioNoticiaVista.usuario_id == usuario_id)
        ).all()
    )

    statement = select(Noticia).order_by(Noticia.created_at.desc())
    noticias = session.exec(statement).all()
    return [noticia for noticia in noticias if noticia.id not in sent_ids][:limit]


def registrar_envio(session: Session, usuario_id: int, noticias: Iterable[Noticia]) -> None:
    for noticia in noticias:
        session.add(UsuarioNoticiaVista(usuario_id=usuario_id, noticia_id=noticia.id, visto=False))
    session.commit()


def enviar_noticias_pendientes(session: Session, limit_por_usuario: int = 5) -> dict[str, object]:
    asegurar_usuarios_base(session)

    bot = BotWhatsApp(**ENV.EVOLUTION_CREDENCIALS)
    usuarios = session.exec(select(Usuario).where(Usuario.activo == True)).all()

    resultado: dict[str, object] = {"usuarios": [], "total_envios": 0}

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
