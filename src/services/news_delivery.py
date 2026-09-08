from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Iterable

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

import config as ENV
from models import Noticia, Usuario, UsuarioNoticiaVista
from utils import BotWhatsApp


LOGGER = logging.getLogger(__name__)
MAX_NEWS_AGE_DAYS = ENV.MAX_NEWS_AGE_DAYS


def _bloque_noticia(idx: int, noticia: Noticia) -> str:
    excerpt = (noticia.excerpt or "").strip()
    excerpt_line = f" — {excerpt}" if excerpt else ""
    fecha = f" | {noticia.date_preview.strftime('%d/%m/%Y')}" if noticia.date_preview else ""
    return f"{idx}. {noticia.title} ({noticia.source}{fecha}){excerpt_line}\n{noticia.url}"


def _build_message(usuario: Usuario, noticias: Iterable[Noticia]) -> str:
    """El envío completo en un solo string. Solo para inspección y tests."""
    noticias = list(noticias)
    saludo = f"Hola {usuario.nombre}, aquí van tus noticias nuevas:"
    bloques = [saludo] + [_bloque_noticia(i, n) for i, n in enumerate(noticias, start=1)]
    return "\n\n".join(bloques)


def construir_mensajes(
    usuario: Usuario,
    noticias: Iterable[Noticia],
    max_chars: int = ENV.MAX_CARACTERES_MENSAJE,
) -> list[tuple[str, list[Noticia]]]:
    """
    Arma el envío como una lista de `(texto, noticias_incluidas)`.

    WhatsApp corta un mensaje en 4.096 caracteres y cada noticia pesa ~450, así
    que un envío de 20 no cabe en uno solo: se parte en varios. Cada parte viaja
    con las noticias que contiene para poder marcar como enviadas **solo** las
    que de verdad salieron — si la parte 2 falla, sus noticias quedan pendientes
    para la próxima corrida en vez de darse por vistas.

    La numeración es continua entre partes: el usuario ve 1..20 corridos, no
    dos listas que empiezan en 1.
    """
    noticias = list(noticias)
    if not noticias:
        return []

    saludo = f"Hola {usuario.nombre}, aquí van tus noticias nuevas:"

    partes: list[tuple[list[str], list[Noticia]]] = []
    actual_bloques: list[str] = [saludo]
    actual_noticias: list[Noticia] = []
    largo = len(saludo)

    for idx, noticia in enumerate(noticias, start=1):
        bloque = _bloque_noticia(idx, noticia)
        # +2 por el "\n\n" que une los bloques.
        if actual_noticias and largo + len(bloque) + 2 > max_chars:
            partes.append((actual_bloques, actual_noticias))
            actual_bloques, actual_noticias, largo = [], [], 0
        actual_bloques.append(bloque)
        actual_noticias.append(noticia)
        largo += len(bloque) + 2

    if actual_noticias:
        partes.append((actual_bloques, actual_noticias))

    total = len(partes)
    mensajes: list[tuple[str, list[Noticia]]] = []
    for numero, (bloques, incluidas) in enumerate(partes, start=1):
        if total > 1:
            bloques = bloques + [f"({numero}/{total})"]
        mensajes.append(("\n\n".join(bloques), incluidas))
    return mensajes


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


def obtener_noticias_no_enviadas(
    session: Session, usuario_id: int, limit: int = ENV.MAX_NOTICIAS_POR_ENVIO
) -> list[Noticia]:
    """
    Devuelve hasta `limit` noticias pendientes para el usuario, de la más
    reciente a la más antigua. Las pendientes cuya fecha de publicación superó
    `MAX_NEWS_AGE_DAYS` se marcan como `omitida_antigua` y no se devuelven.

    El filtrado ocurre en SQL: la tabla `noticia` crece sin techo y no debe
    cargarse completa en memoria por cada usuario y cada corrida.
    """
    ya_vistas = select(UsuarioNoticiaVista.noticia_id).where(
        UsuarioNoticiaVista.usuario_id == usuario_id
    )

    # Postgres promueve `date` a timestamp a medianoche, así que comparar la
    # columna date contra este datetime mantiene el criterio original.
    cutoff = datetime.now() - timedelta(days=MAX_NEWS_AGE_DAYS)

    vencidas = session.execute(
        select(Noticia).where(
            Noticia.id.not_in(ya_vistas),
            Noticia.date_preview.is_not(None),
            Noticia.date_preview < cutoff,
        )
    ).scalars().all()

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

    # Las noticias sin `date_preview` nunca vencen: se tratan como recientes,
    # igual que en la implementación anterior.
    return list(
        session.execute(
            select(Noticia)
            .where(
                Noticia.id.not_in(ya_vistas),
                or_(Noticia.date_preview.is_(None), Noticia.date_preview >= cutoff),
            )
            .order_by(Noticia.created_at.desc())
            .limit(limit)
        ).scalars().all()
    )


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


def enviar_noticias_pendientes(
    session: Session, limit_por_usuario: int = ENV.MAX_NOTICIAS_POR_ENVIO
) -> dict[str, object]:
    bot = BotWhatsApp(**ENV.EVOLUTION_CREDENCIALS)
    usuarios = session.execute(select(Usuario).where(Usuario.activo == True)).scalars().all()

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

        mensajes = construir_mensajes(usuario, noticias)
        enviadas = 0
        response: dict = {}
        ok = True

        # Se corta en la primera parte que falla: seguir mandando dejaría al
        # usuario con la lista salteada, y las que no salieron vuelven a estar
        # pendientes en la próxima corrida.
        for mensaje, incluidas in mensajes:
            response = bot.enviar_mensaje(usuario.whatsapp, mensaje, delay=1200)
            if not response.get("ok"):
                ok = False
                LOGGER.warning(
                    "Envío parcial usuario=%s enviadas=%s de %s error=%s",
                    usuario.whatsapp,
                    enviadas,
                    len(noticias),
                    response.get("error"),
                )
                break
            registrar_envio(session, usuario.id, incluidas)
            enviadas += len(incluidas)

        resultado["total_envios"] = int(resultado["total_envios"]) + enviadas

        resultado["usuarios"].append(
            {
                "usuario": usuario.nombre,
                "numero": usuario.whatsapp,
                "enviadas": enviadas,
                "partes": len(mensajes),
                "status": "ok" if ok else "error",
                "response": response,
            }
        )

    return resultado
