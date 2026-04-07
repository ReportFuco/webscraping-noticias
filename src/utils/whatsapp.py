from __future__ import annotations

from io import BytesIO
from typing import Literal
import base64
import logging
from pathlib import Path

import httpx


LOGGER = logging.getLogger(__name__)


class BotWhatsApp:
    """
    Wrapper simple para Evolution API usando httpx.
    Permite enviar mensajes, botones, stickers e imágenes.
    """

    def __init__(self, url: str, instance: str, api_key: str, timeout: float = 30.0):
        self.url = url.rstrip("/")
        self.instance = instance
        self.api_key = api_key
        self.timeout = timeout

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self.api_key,
            "Content-Type": "application/json",
        }

    def _post(self, endpoint: str, payload: dict) -> dict[Literal["ok", "status_code", "data", "error"], object]:
        url = f"{self.url}{endpoint}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(url, headers=self._headers, json=payload)

            data: object
            try:
                data = res.json()
            except ValueError:
                data = res.text

            ok = res.status_code in (200, 201)
            if ok:
                LOGGER.info("Evolution OK endpoint=%s status=%s", endpoint, res.status_code)
            else:
                LOGGER.warning(
                    "Evolution error endpoint=%s status=%s body=%s",
                    endpoint,
                    res.status_code,
                    data,
                )

            return {
                "ok": ok,
                "status_code": res.status_code,
                "data": data,
                "error": None if ok else str(data),
            }
        except httpx.HTTPError as exc:
            LOGGER.exception("Evolution request failed endpoint=%s", endpoint)
            return {
                "ok": False,
                "status_code": None,
                "data": None,
                "error": str(exc),
            }

    def enviar_mensaje(
        self,
        numero: str,
        mensaje: str,
        delay: int | None = None,
    ) -> dict[Literal["ok", "status_code", "data", "error"], object]:
        payload = {
            "number": numero,
            "text": mensaje,
        }
        if delay is not None:
            payload["delay"] = delay
        return self._post(f"/message/sendText/{self.instance}", payload)

    def enviar_mensaje_con_boton(
        self,
        numero: str,
        titulo: str,
        descripcion: str,
        footer: str,
        botones: list[str],
    ) -> dict[Literal["ok", "status_code", "data", "error"], object]:
        return self._post(
            f"/message/sendButtons/{self.instance}",
            {
                "number": numero,
                "title": titulo,
                "description": descripcion,
                "footer": footer,
                "buttons": botones,
            },
        )

    def enviar_sticker(
        self,
        numero: str,
        sticker: str,
        delay: int | None = None,
    ) -> dict[Literal["ok", "status_code", "data", "error"], object]:
        payload = {
            "number": numero,
            "sticker": sticker,
        }
        if delay is not None:
            payload["delay"] = delay
        return self._post(f"/message/sendSticker/{self.instance}", payload)

    def enviar_mensaje_foto(
        self,
        numero: str,
        mensaje: str,
        path_foto: str | None = None,
        buffer: BytesIO | None = None,
        delay: int | None = None,
        mimetype: str = "image/jpeg",
    ) -> dict[Literal["ok", "status_code", "data", "error"], object]:
        if path_foto and buffer:
            raise ValueError("Solo puedes proporcionar 'path_foto' o 'buffer', no ambos.")
        if not path_foto and not buffer:
            raise ValueError("Debes proporcionar al menos 'path_foto' o 'buffer'.")

        if buffer:
            buffer.seek(0)
            img = base64.b64encode(buffer.read()).decode("utf-8")
        else:
            with open(path_foto, "rb") as file:
                img = base64.b64encode(file.read()).decode("utf-8")

        payload = {
            "media": img,
            "caption": mensaje,
            "mediatype": "image",
            "number": numero,
            "mimetype": mimetype,
        }
        if delay is not None:
            payload["delay"] = delay
        return self._post(f"/message/sendMedia/{self.instance}", payload)

    def enviar_documento(
        self,
        numero: str,
        path_archivo: str | None = None,
        buffer: BytesIO | None = None,
        file_name: str | None = None,
        caption: str = "",
        delay: int | None = None,
        mimetype: str = "application/octet-stream",
    ) -> dict[Literal["ok", "status_code", "data", "error"], object]:
        if path_archivo and buffer:
            raise ValueError("Solo puedes proporcionar 'path_archivo' o 'buffer', no ambos.")
        if not path_archivo and not buffer:
            raise ValueError("Debes proporcionar al menos 'path_archivo' o 'buffer'.")

        if buffer:
            if not file_name:
                raise ValueError("Si usas 'buffer', debes indicar 'file_name'.")
            buffer.seek(0)
            media = base64.b64encode(buffer.read()).decode("utf-8")
        else:
            with open(path_archivo, "rb") as file:
                media = base64.b64encode(file.read()).decode("utf-8")
            if not file_name:
                file_name = Path(path_archivo).name

        payload = {
            "number": numero,
            "mediatype": "document",
            "mimetype": mimetype,
            "caption": caption,
            "media": media,
            "fileName": file_name,
        }
        if delay is not None:
            payload["delay"] = delay
        return self._post(f"/message/sendMedia/{self.instance}", payload)


EvolutionWhatsApp = BotWhatsApp
