"""
Detección de fuentes que dejan de rendir sin fallar.

Un scraper cuyo sitio cambió el HTML no lanza excepción: devuelve cero
noticias, `_run_scraper` lo da por bueno y la fila queda `status='ok'` con
`reviewed_count=0`. Es el modo de falla más probable de un scraper y hasta
ahora era invisible: había que mirar la tabla a mano para notarlo.

Acá se marca ese caso como `vacia` en `scraperunsource.status` y se avisa por
WhatsApp cuando se repite. `status` es texto libre, así que no hace falta
migración.

**Se avisa una sola vez, al cruzar el umbral.** Una fuente rota sigue vacía en
todas las corridas siguientes, y con el cron cada dos horas eso serían doce
mensajes al día por la misma noticia. El aviso se vuelve a armar solo si la
fuente se recupera y vuelve a caer.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import ScrapeRunSource
from utils.whatsapp import BotWhatsApp


LOGGER = logging.getLogger("news_scraper")

ESTADO_VACIA = "vacia"


def contar_racha(estados: list[str]) -> int:
    """
    Cuántos estados seguidos, desde el más reciente hacia atrás, son `vacia`.

    Recibe la lista ya ordenada de más nuevo a más viejo. Es una función pura
    para poder probar la regla sin base de datos.
    """
    racha = 0
    for estado in estados:
        if estado != ESTADO_VACIA:
            break
        racha += 1
    return racha


def racha_vacia(session: Session, source: str, limite: int) -> int:
    """
    Corridas consecutivas que la fuente terminó vacía, contando la actual.

    Se consultan solo `limite` filas porque no interesa el largo real de la
    racha, sino si llegó al umbral.
    """
    estados = (
        session.execute(
            select(ScrapeRunSource.status)
            .where(ScrapeRunSource.source == source)
            .order_by(ScrapeRunSource.scrape_run_id.desc())
            .limit(limite)
        )
        .scalars()
        .all()
    )
    return contar_racha(list(estados))


def fuentes_a_avisar(session: Session, vacias: list[str], umbral: int) -> list[str]:
    """
    De las fuentes vacías en esta corrida, las que recién cruzaron el umbral.

    La comparación es por igualdad y no por `>=` a propósito: es lo que hace
    que el aviso salga una sola vez. Ver el docstring del módulo.

    Por eso se piden `umbral + 1` filas y no `umbral`: pidiendo justo el umbral,
    una fuente rota hace diez corridas devuelve una racha de exactamente
    `umbral` —la consulta no alcanza a ver la corrida anterior— y el aviso
    vuelve a salir en cada ciclo. La fila extra es la que distingue "acaba de
    cruzar" de "sigue rota".
    """
    if umbral < 1:
        return []
    return [
        source
        for source in vacias
        if racha_vacia(session, source, umbral + 1) == umbral
    ]


def mensaje_alerta(fuentes: list[str], umbral: int) -> str:
    """Texto del aviso. Separado del envío para poder probarlo sin red."""
    corridas = "corrida" if umbral == 1 else "corridas"
    encabezado = (
        f"⚠️ Scraper de noticias\n\n"
        f"{len(fuentes)} fuente{'s' if len(fuentes) > 1 else ''} "
        f"sin resultados en {umbral} {corridas} seguidas:"
    )
    listado = "\n".join(f"• {fuente}" for fuente in sorted(fuentes))
    cierre = (
        "\nProbablemente el sitio cambió su HTML. No vuelvo a avisar de estas "
        "hasta que se recuperen."
    )
    return f"{encabezado}\n{listado}\n{cierre}"


def avisar_fuentes_vacias(
    fuentes: list[str],
    umbral: int,
    destinos: list[str],
    credenciales: dict[str, str],
) -> int:
    """
    Manda el aviso por WhatsApp. Devuelve cuántos envíos salieron bien.

    No propaga errores: un aviso que falla no puede voltear la corrida que lo
    generó, que para ese punto ya guardó todo lo que tenía que guardar. Sin
    `destinos` configurados solo queda el log, que es el comportamiento por
    defecto.
    """
    if not fuentes:
        return 0

    LOGGER.error(
        "Fuentes sin resultados en %s corridas seguidas: %s",
        umbral,
        ", ".join(sorted(fuentes)),
    )

    if not destinos:
        LOGGER.warning(
            "Sin ALERTA_WHATSAPP configurado: el aviso queda solo en el log"
        )
        return 0

    if not all(credenciales.get(clave) for clave in ("url", "instance", "api_key")):
        LOGGER.warning("Evolution API sin credenciales: el aviso queda solo en el log")
        return 0

    bot = BotWhatsApp(**credenciales)
    texto = mensaje_alerta(fuentes, umbral)
    enviados = 0

    for numero in destinos:
        try:
            resultado = bot.enviar_mensaje(numero, texto)
        except Exception:
            LOGGER.exception("Aviso de fuentes vacías falló destino=%s", numero)
            continue
        if resultado.get("ok"):
            enviados += 1
        else:
            LOGGER.warning(
                "Aviso de fuentes vacías rechazado destino=%s error=%s",
                numero,
                resultado.get("error"),
            )

    return enviados
