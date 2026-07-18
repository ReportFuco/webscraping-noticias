# Noticias API — Referencia

API REST construida con FastAPI para consultar y gestionar las noticias scrapeadas del proyecto. Corre en PostgreSQL (async via SQLAlchemy).

## Base URL

```
https://api.supermercadoaldia.cl
```

La documentación interactiva está en `/docs` (Swagger) y `/redoc`.

---

## Autenticación

La API tiene dos mecanismos de autenticación, con roles separados:

### 1. API Key (recursos de negocio: noticias, scraper, webhooks)

Todos los endpoints bajo `/noticias`, `/scraper` y `/webhooks` requieren la cabecera:

```
X-API-Key: <tu-api-key>
```

Las API keys **ya no se generan automáticamente al registrarte**: un usuario puede tener **varias**, las crea y revoca él mismo desde `/me/api-keys` (requiere estar logueado por JWT). Cada key se muestra en texto plano **una única vez**, al crearla — después solo se guarda su hash.

Condiciones para que una key funcione:
- Debe estar activa (no revocada).
- La cuenta dueña debe tener `is_active = true` y **`is_verified = true`** (ver registro más abajo).

Si falta, es inválida, o la cuenta no está verificada → `401`/`403`. `/scraper` y `/webhooks` además requieren que el usuario dueño de la key tenga `is_superuser = true` → si no, `403 Forbidden`.

> Nota: el JWT (sección 2) **no** protege ningún recurso de negocio, solo la gestión de la cuenta y de las api keys (`/auth/*`, `/users/*`, `/me/api-keys`).

### 2. JWT Bearer (gestión de usuarios y de API keys)

Los endpoints de `/users` y `/me/api-keys` requieren:

```
Authorization: Bearer <jwt-token>
```

El token se obtiene en `POST /auth/jwt/login`. Tiene validez de **30 días**.

---

## Endpoints

### Salud

Sin autenticación. Pensados para monitoreo/health checks (no cuentan contra ningún límite de negocio).

#### `GET /health`

Chequeo de vida del proceso, no toca la base de datos. Responde `200 {"status": "ok"}` mientras la API esté arriba.

#### `GET /ready`

Chequeo de disponibilidad real: ejecuta `SELECT 1` contra Postgres. `200 {"status": "ok"}` si la DB responde, `503` si no.

---

### Autenticación de usuarios

#### `POST /auth/register`

Registra un nuevo usuario. La cuenta nace **sin verificar** (`is_verified: false`) y dispara automáticamente un token de verificación (ver `POST /auth/verify` abajo).

**Body (JSON):**
```json
{
  "email": "usuario@ejemplo.com",
  "password": "contraseña-segura"
}
```

**Respuesta exitosa `201`:**
```json
{
  "id": "uuid-del-usuario",
  "email": "usuario@ejemplo.com",
  "is_active": true,
  "is_superuser": false,
  "is_verified": false
}
```

> **Importante:** hasta que la cuenta esté verificada, ninguna API key creada bajo ella funciona (`403` en cualquier endpoint que use `X-API-Key`). Verificá antes de crear tus keys.

---

#### `POST /auth/request-verify-token`

Reenvía el token de verificación si no llegó o expiró (1 hora de validez).

**Body (JSON):** `{"email": "usuario@ejemplo.com"}`. Responde `202` siempre (no filtra si el email existe).

#### `POST /auth/verify`

Verifica la cuenta con el token recibido al registrarse (o al pedirlo de nuevo).

**Body (JSON):** `{"token": "eyJ..."}`

**Respuesta `200`:** el usuario con `is_verified: true`.

> **Limitación actual:** no hay envío automático de email/WhatsApp con el token todavía — queda registrado en `logs/api.log` y hay que entregarlo manualmente al usuario. Ver `docs/auditoria/ROADMAP.md` (T1.1) para el plan de conectar un canal real.

---

#### `POST /auth/jwt/login`

Obtiene un JWT para el usuario registrado.

**Body (form-data):**
```
username=usuario@ejemplo.com
password=contraseña-segura
```

**Respuesta exitosa `200`:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

---

#### `POST /auth/jwt/logout`

Invalida la sesión actual. Requiere `Authorization: Bearer <token>`.

---

### Usuarios

#### `GET /users/me`

Devuelve el perfil del usuario autenticado (JWT).

**Respuesta `200`:**
```json
{
  "id": "uuid",
  "email": "usuario@ejemplo.com",
  "is_active": true,
  "is_superuser": false,
  "is_verified": true
}
```

#### `PATCH /users/me`

Actualiza email o contraseña del usuario autenticado.

---

### API Keys (`/me/api-keys`)

> Requiere JWT (`Authorization: Bearer <token>`). Gestiona las API keys del usuario logueado — no hay endpoint para ver/gestionar las keys de otro usuario.

#### `GET /me/api-keys`

Lista las keys del usuario, **sin exponer el secreto**.

**Respuesta `200`:**
```json
[
  {
    "id": 3,
    "name": "integracion-n8n",
    "key_prefix": "AO6zU_3b",
    "is_active": true,
    "created_at": "2026-07-01T18:47:47.076277",
    "last_used_at": "2026-07-01T19:02:11.442310"
  }
]
```

#### `POST /me/api-keys`

Crea una key nueva.

**Body (JSON):** `{"name": "integracion-n8n"}`

**Respuesta `201`:**
```json
{
  "id": 3,
  "name": "integracion-n8n",
  "key_prefix": "AO6zU_3b",
  "is_active": true,
  "created_at": "2026-07-01T18:47:47.076277",
  "last_used_at": null,
  "api_key": "AO6zU_3beK-VY86KPLE53LMaDt8fVubHJrGJKbBbPk8"
}
```

> **El campo `api_key` solo aparece en esta respuesta.** No hay forma de recuperar el valor completo después — si se pierde, hay que revocar la key y crear una nueva.

#### `DELETE /me/api-keys/{id}`

Revoca la key (soft-delete: `is_active=false`). No se puede reactivar vía API. `404` si el `id` no existe o no pertenece al usuario logueado.

**Respuesta `204`.**

---

### Noticias

> Todos los endpoints de esta sección requieren `X-API-Key`.

#### `GET /noticias`

Lista noticias con paginación y filtros opcionales. Ordenadas por `id` descendente (más recientemente ingresadas primero). No se ordena por `date_preview` porque ese campo puede venir nulo o mal parseado según la fuente, lo que distorsionaría el orden.

**Query params:**

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `source` | string | — | Filtrar por fuente (ej: `"walmartchile"`) |
| `country` | string | — | Filtrar por país (ej: `"CL"`) |
| `score_min` | int ≥ 0 | `0` | Score mínimo de relevancia |
| `desde` | date `YYYY-MM-DD` | — | Publicadas desde esta fecha |
| `hasta` | date `YYYY-MM-DD` | — | Publicadas hasta esta fecha |
| `buscar` | string | — | Búsqueda de texto libre en título y bajada (case-insensitive) |
| `limit` | int 1–100 | `20` | Resultados por página |
| `offset` | int ≥ 0 | `0` | Desplazamiento para paginación |

**Respuesta `200`:**
```json
{
  "total": 142,
  "limit": 20,
  "offset": 0,
  "items": [
    {
      "id": 1,
      "title": "Walmart Chile abre nuevo local en Maipú",
      "url": "https://...",
      "img": "https://...",
      "date_preview": "2026-05-19",
      "source": "walmartchile",
      "country": "CL",
      "excerpt": "La cadena de supermercados anunció...",
      "score": 12,
      "created_at": "2026-05-19T08:30:00"
    }
  ]
}
```

**Ejemplos:**
```bash
# Noticias relevantes de la última semana
curl -H "X-API-Key: $API_KEY" \
  "https://api.supermercadoaldia.cl/noticias?score_min=5&desde=2026-05-12"

# Buscar noticias que mencionen "Cencosud" en título o bajada
curl -H "X-API-Key: $API_KEY" \
  "https://api.supermercadoaldia.cl/noticias?buscar=Cencosud"
```

---

#### `GET /noticias/{id}`

Devuelve una noticia por su ID numérico.

**Respuesta `200`:** misma estructura que un ítem de la lista.

**Respuesta `404`:**
```json
{ "detail": "Noticia no encontrada" }
```

---

#### `PATCH /noticias/{id}`

Actualiza el título o el excerpt de una noticia. Útil para correcciones editoriales o enriquecimiento por un agente.

**Body (JSON, todos los campos opcionales):**
```json
{
  "title": "Título corregido",
  "excerpt": "Resumen mejorado del artículo..."
}
```

**Respuesta `200`:** la noticia actualizada completa.

---

## Modelo de datos — Noticia

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | int | Clave primaria |
| `title` | string | Titular del artículo |
| `url` | string | URL original (único) |
| `img` | string | URL de imagen de portada |
| `date_preview` | date \| null | Fecha de publicación parseada (`YYYY-MM-DD`); null si el scraper no pudo determinarla |
| `source` | string | Identificador del scraper de origen |
| `country` | string | País (`"CL"` por defecto) |
| `excerpt` | string \| null | Bajada/resumen del artículo |
| `score` | int | Puntuación de relevancia (scorer interno) |
| `created_at` | datetime | Timestamp de ingesta en el sistema |

---

### Scraper

> Requiere `X-API-Key` de un usuario con `is_superuser = true` (no JWT).

#### `POST /scraper/run`

Dispara el pipeline completo de scraping en background y responde inmediatamente. El proceso corre de forma asíncrona: la respuesta llega antes de que el scraping termine.

**Respuesta `200`:**
```json
{
  "status": "started",
  "message": "Scraping iniciado en background"
}
```

**Errores:**
- `401` — API key ausente o inválida
- `403` — usuario no es superuser

---

### Webhooks

> Requiere `X-API-Key` de un usuario con `is_superuser = true`.

Permiten registrar destinos HTTP que reciben un evento cada vez que el pipeline de scraping termina y encuentra noticias nuevas.

#### `GET /webhooks`

Lista los webhooks registrados.

#### `POST /webhooks`

Crea un webhook.

**Body (JSON):**
```json
{
  "name": "mi-integracion",
  "url": "https://mi-servicio.com/hooks/noticias",
  "secret": "un-secreto-de-al-menos-8-caracteres"
}
```

**Respuesta `201`:** el webhook creado (no incluye `secret` en la respuesta).

#### `PATCH /webhooks/{id}`

Actualiza `name`, `url`, `secret` y/o `is_active` (todos opcionales).

#### `DELETE /webhooks/{id}`

Elimina el webhook. Respuesta `204`.

**Evento disparado (`scrape_completed`):**

Al terminar cada corrida de scraping, si hubo noticias nuevas, se hace `POST` a la `url` de cada webhook **activo** con:

```json
{
  "event": "scrape_completed",
  "scrape_run_id": 123,
  "total_new": 5,
  "noticias": [ /* mismos campos que un ítem de /noticias, sin id de usuario */ ]
}
```

Cabecera `X-Webhook-Secret: <secret>` con el secreto configurado al crear el webhook (el receptor debe validarlo). Timeout de 10s; si falla, se loguea y no se reintenta.

---

## Notas

- **Paginación:** usar `offset` + `limit` para iterar. El campo `total` indica el total de resultados para la consulta.
- **Score:** el sistema descarta automáticamente noticias con `score < 3`. Noticias con `score ≥ 8` son altamente relevantes para el dominio retail/supermercados Chile.
- **Búsqueda de texto (`buscar`):** aplica `ILIKE %término%` sobre `title` y `excerpt` en simultáneo. Case-insensitive, sin normalización de acentos.
- **Fuentes disponibles:** no hay endpoint de listado de fuentes; se pueden inferir consultando con distintos valores de `source`, o revisando `config.SCRAPERS` en el código.
- **Deduplicación:** la URL es única en el sistema; si el scraper encuentra la misma URL en distintas corridas, solo existe un registro.
- **PATCH es seguro de usar:** solo modifica `title` y `excerpt`; no afecta scoring ni metadatos del scraper.
