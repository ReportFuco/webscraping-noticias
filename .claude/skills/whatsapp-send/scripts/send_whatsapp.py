#!/usr/bin/env python3
"""Envía un mensaje de WhatsApp via Evolution API.

Autocontenido: no depende de src/config.py ni de src/utils del repo, solo de
'httpx' y 'python-dotenv' (ya presentes en el .venv de este proyecto). Busca
un .env hacia arriba desde este archivo y lee tres variables de entorno:

    URL_EVOLUTION      - URL base de la instancia Evolution API
    INSTANCE_EVOLUTION - nombre de la instancia
    APIKEY_EVOLUTION   - API key de la instancia

Si falta alguna, avisa cuáles (solo los NOMBRES, nunca los valores) y no
intenta enviar nada. Pensado para copiarse a otro repo tal cual: si ese repo
no tiene un .env con esas variables, el mensaje de error deja claro qué hay
que configurar.
"""
from __future__ import annotations

import argparse
import os
import sys

REQUIRED_VARS = ["URL_EVOLUTION", "INSTANCE_EVOLUTION", "APIKEY_EVOLUTION"]


def _load_dotenv_if_available() -> None:
    try:
        from dotenv import find_dotenv, load_dotenv
    except ImportError:
        return
    load_dotenv(find_dotenv(usecwd=True))


def _missing_vars() -> list[str]:
    return [name for name in REQUIRED_VARS if not os.getenv(name)]


def _enviar_mensaje(url: str, instance: str, api_key: str, numero: str, mensaje: str) -> tuple[bool, str]:
    import httpx

    endpoint = f"{url.rstrip('/')}/message/sendText/{instance}"
    headers = {"apikey": api_key, "Content-Type": "application/json"}
    payload = {"number": numero, "text": mensaje}

    try:
        response = httpx.post(endpoint, headers=headers, json=payload, timeout=30.0)
    except httpx.HTTPError as exc:
        return False, str(exc)

    if response.status_code in (200, 201):
        return True, str(response.status_code)

    try:
        detail = response.json()
    except ValueError:
        detail = response.text
    return False, f"HTTP {response.status_code}: {detail}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--numero", required=True, help="Numero destino, formato 569XXXXXXXX")
    parser.add_argument("--mensaje", required=True, help="Texto del mensaje a enviar")
    args = parser.parse_args()

    _load_dotenv_if_available()

    faltantes = _missing_vars()
    if faltantes:
        print(
            "No se puede enviar: faltan estas variables en el .env "
            f"({', '.join(faltantes)}). Configura Evolution API y "
            "vuelve a intentar; esta skill no necesita nada más.",
            file=sys.stderr,
        )
        return 1

    ok, detalle = _enviar_mensaje(
        url=os.environ["URL_EVOLUTION"],
        instance=os.environ["INSTANCE_EVOLUTION"],
        api_key=os.environ["APIKEY_EVOLUTION"],
        numero=args.numero,
        mensaje=args.mensaje,
    )

    if ok:
        print(f"Enviado OK a {args.numero} (status {detalle})")
        return 0

    print(f"Error al enviar a {args.numero}: {detalle}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
