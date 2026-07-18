---
name: whatsapp-send
description: Envía un mensaje de WhatsApp a un número usando Evolution API. Úsala cuando el usuario pida avisar, notificar o mandar algo por WhatsApp a un número o contacto. Autocontenida — funciona en cualquier repo que tenga un .env con URL_EVOLUTION, INSTANCE_EVOLUTION y APIKEY_EVOLUTION.
user-invocable: true
allowed-tools:
  - Bash(*/send_whatsapp.py:*)
---

# Enviar mensajes de WhatsApp (Evolution API)

## Requisitos

Esta skill necesita un `.env` (en la raíz del repo donde se ejecute) con:

- `URL_EVOLUTION` — URL base de la instancia Evolution API
- `INSTANCE_EVOLUTION` — nombre de la instancia
- `APIKEY_EVOLUTION` — API key de la instancia

En **este** proyecto (webscraping-noticias) ya están configuradas — no hay
que hacer nada extra aquí.

Si copias esta skill a otro repo/servidor que no tenga esas variables, el
script falla solo con un mensaje tipo `No se puede enviar: faltan estas
variables en el .env (URL_EVOLUTION, ...)`. Nunca imprime valores, solo los
nombres de lo que falta. Si ves ese mensaje: pídele al usuario esas tres
credenciales, ponlas en el `.env` de ese repo, y reintenta — no hace falta
tocar el script.

## Regla de seguridad

**Nunca leas, imprimas ni pegues el contenido de `.env` en la conversación.**
El script carga las credenciales por su cuenta; tu trabajo es solo pasarle
número y mensaje.

Enviar un WhatsApp es una acción real e irreversible (no se puede
"desenviar"). Antes de ejecutar el script, confirma con el usuario:
- el número de destino (formato `56XXXXXXXXX`, sin `+` ni espacios)
- el texto exacto que se va a enviar

Si el usuario ya dio ambos datos explícitamente en su pedido, puedes enviar
directo sin volver a preguntar.

## Cómo enviar

```bash
python3 .claude/skills/whatsapp-send/scripts/send_whatsapp.py \
  --numero "56XXXXXXXXX" \
  --mensaje "texto del mensaje"
```

(En este proyecto usa `.venv/bin/python` en vez de `python3` si el venv
está activo — el script solo necesita `httpx`, y `python-dotenv` si lo hay.)

Salidas posibles:
- `Enviado OK a <numero> (status <code>)` — funcionó.
- `No se puede enviar: faltan estas variables en el .env (...)` — falta
  configuración, no es un bug.
- `Error al enviar a <numero>: ...` — Evolution API respondió con error
  (número inválido, instancia caída, etc.).

## Notas

- Solo envía texto plano. Para documentos/CSV o imágenes hay que armar un
  script aparte que use el endpoint `sendMedia` de Evolution API (en este
  repo, ver `src/utils/whatsapp.py` para el patrón ya usado).
- Los números de los usuarios activos de este sistema están en la tabla
  `usuario` de la base de datos, no en este repo de skills.
