# Noticias API — Referencia

API REST construida con FastAPI para consultar y gestionar las noticias scrapeadas del proyecto. Corre en PostgreSQL (async via SQLAlchemy).

## Base URL

```
https://api.supermercadoaldia.cl
```

La documentación interactiva está en `/docs` (Swagger) y `/redoc`.

---

## Autenticación

La API tiene dos mecanismos de autenticación, según el recurso:

### 1. API Key (recursos de noticias)

Todos los endpoints bajo `/noticias` requieren la cabecera:

```
X-API-Key: <tu-api-key>
```

La API key se genera automáticamente al registrar un usuario (campo `api_key` en la respuesta). Es un token URL-safe de 64 caracteres.

Si falta o es inválida → `401 Unauthorized`.

### 2. JWT Bearer (gestión de usuarios)

Los endpoints de `/users` requieren:

```
Authorization: Bearer <jwt-token>
```

El token se obtiene en `POST /auth/jwt/login`. Tiene validez de **30 días**.

---

## Endpoints

### Autenticación de usuarios

#### `POST /auth/register`

Registra un nuevo usuario. Al crearse, se genera una `api_key` automáticamente.

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
  "is_verified": false,
  "api_key": "tu-api-key-de-64-chars"
}
```

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

Devuelve el perfil del usuario autenticado (JWT). Útil para recuperar la `api_key` si se perdió.

**Respuesta `200`:**
```json
{
  "id": "uuid",
  "email": "usuario@ejemplo.com",
  "is_active": true,
  "api_key": "tu-api-key"
}
```

#### `PATCH /users/me`

Actualiza email o contraseña del usuario autenticado.

---

### Noticias

> Todos los endpoints de esta sección requieren `X-API-Key`.

#### `GET /noticias`

Lista noticias con paginación y filtros opcionales. Ordenadas por fecha de publicación descendente (más recientes primero).

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

> Requiere autenticación JWT (`Authorization: Bearer <token>`) de un usuario con `is_superuser = true`.

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
- `401` — token ausente o inválido
- `403` — usuario no es superuser

---

## Notas

- **Paginación:** usar `offset` + `limit` para iterar. El campo `total` indica el total de resultados para la consulta.
- **Score:** el sistema descarta automáticamente noticias con `score < 3`. Noticias con `score ≥ 8` son altamente relevantes para el dominio retail/supermercados Chile.
- **Búsqueda de texto (`buscar`):** aplica `ILIKE %término%` sobre `title` y `excerpt` en simultáneo. Case-insensitive, sin normalización de acentos.
- **Fuentes disponibles:** no hay endpoint de listado de fuentes; se pueden inferir consultando con distintos valores de `source`, o revisando `config.SCRAPERS` en el código.
- **Deduplicación:** la URL es única en el sistema; si el scraper encuentra la misma URL en distintas corridas, solo existe un registro.
- **PATCH es seguro de usar:** solo modifica `title` y `excerpt`; no afecta scoring ni metadatos del scraper.
