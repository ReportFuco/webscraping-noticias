# Auditoría de la API — Noticias

> Auditoría técnica de la capa API (`src/api/**`) del proyecto de scraping de noticias.
> Fecha: 2026-07-01 · Alcance: autenticación, endpoints, seguridad, rendimiento, operación.

Esta carpeta contiene un plan de mejora accionable. Está pensada para que **un agente (o dev) pueda avanzar tarea por tarea** sin tener que redescubrir el contexto.

## Archivos

| Archivo | Para qué sirve |
|---|---|
| `README.md` | Este documento. Resumen ejecutivo + tabla de hallazgos + cómo trabajar. |
| `hallazgos.md` | Catálogo detallado de cada hallazgo (`H-XX`): evidencia (`archivo:línea`), impacto, remediación, esfuerzo. |
| `ROADMAP.md` | Plan de ejecución por fases, priorizado, con checklists y criterios de aceptación. |
| `auth-decision.md` | Decisión de arquitectura (ADR) sobre JWT vs API Key. **Leer antes de tocar auth.** |

## Cómo trabajar con este plan (para un agente)

1. Lee `auth-decision.md` si la tarea toca autenticación.
2. Abre `ROADMAP.md` y toma la primera tarea no completada de la fase activa.
3. Cada tarea referencia un hallazgo `H-XX` en `hallazgos.md` con el detalle técnico.
4. Al terminar una tarea: marca el checkbox en `ROADMAP.md` y valida el criterio de aceptación.
5. Tras cambios de API: `sudo systemctl restart noticias-api` (Nginx no se toca). Ver `CLAUDE.md`.

## Contexto del stack (verificado)

- **Framework:** FastAPI `0.136.1` / Starlette `1.0.0` / Pydantic `2.12.5`
- **DB:** PostgreSQL vía SQLAlchemy `2.0.48` async (`asyncpg 0.31.0`). Sesión sync también disponible (`psycopg2`).
- **Auth:** `fastapi-users 15.0.5` (JWT, gestión de cuenta + api keys) **+** capa propia de API Key (`X-API-Key`, hasheada, tabla `api_key` con 1 usuario → N keys).
- **Serving:** `gunicorn 26` + `uvicorn` workers (2), `127.0.0.1:8010`, detrás de Nginx (servicio `noticias-api`).
- **Migraciones:** Alembic. Corren como `ExecStartPre` del service (no en el `lifespan` de la app).

## Resumen ejecutivo

> Esta sección describe el estado **al momento de la auditoría** (2026-07-01, antes de ejecutar el roadmap). Para el estado actual real, ver la columna **Estado** en la tabla de hallazgos más abajo — a la fecha, Fase 0 completa y Fase 1 completa (H-01, H-02, H-05, H-06, H-08, H-12, H-13, H-17, H-18 resueltos; H-03 parcial).

La API era **pequeña, limpia y funcional**, pero tenía puntos débiles concentrados en tres áreas:

1. **Autenticación ambigua y expuesta.** Convivían dos sistemas (JWT y API Key) sin una línea divisoria clara; el registro era **público sin gating**, las API keys y los secretos de webhook se guardaban **en texto plano**, y `JWT_SECRET` podía arrancar vacío. Además había una **discrepancia entre la doc y el código** (la doc decía que `/scraper` usaba JWT; el código usa API Key de superuser).
2. **Falta de defensas de borde.** No había rate limiting, ni CORS configurado, ni manejo global de errores, ni endpoint de salud, ni logging de requests. `/docs` es público.
3. **Rendimiento y operación.** Búsqueda `ILIKE %term%` sin índice (full scan al crecer la tabla), paginación por `OFFSET`, pool de conexiones sin `pool_pre_ping`, migraciones corriendo en cada worker al bootear, y `/scraper/run` sin protección contra corridas concurrentes.

Ninguno era catastrófico, pero varios eran **fáciles de explotar o de degradar** a medida que crece el uso. Fases 2 y 3 (rate limiting, errores uniformes, CORS si aplica, lock de scraping, índices de búsqueda, webhooks anti-SSRF) siguen pendientes — ver `ROADMAP.md`.

## Tabla de hallazgos

Severidad: 🔴 Alta · 🟠 Media · 🟡 Baja

| ID | Severidad | Área | Título | Estado |
|----|-----------|------|--------|--------|
| [H-01](hallazgos.md#h-01) | 🔴 | Auth | Registro público otorga acceso de lectura/edición a toda la data | ✅ Resuelto |
| [H-02](hallazgos.md#h-02) | 🔴 | Auth | `JWT_SECRET` y `API_KEY` con default vacío (`""`) — tokens forjables si no se setea | ✅ Resuelto |
| [H-03](hallazgos.md#h-03) | 🔴 | Auth | API keys y secretos de webhook almacenados en texto plano | ⚠️ Parcial: keys ✅, webhook secret pendiente (Fase 3) |
| [H-04](hallazgos.md#h-04) | 🟠 | Seguridad | Sin rate limiting en ningún endpoint | Pendiente (Fase 2) |
| [H-05](hallazgos.md#h-05) | 🟠 | Docs/Auth | Discrepancia doc↔código: `/scraper` documentado como JWT, implementado con API Key | ✅ Resuelto |
| [H-06](hallazgos.md#h-06) | 🟠 | Auth | `PATCH /noticias/{id}` editable por **cualquier** usuario con API key (sin superuser) | ✅ Resuelto |
| [H-07](hallazgos.md#h-07) | 🟠 | Seguridad | Webhooks: SSRF posible + secreto enviado plano (no firma HMAC), sin reintentos | Pendiente (Fase 3) |
| [H-08](hallazgos.md#h-08) | 🟠 | Operación | `alembic upgrade head` en cada worker al arrancar (posible race con 2 workers) | ✅ Resuelto |
| [H-09](hallazgos.md#h-09) | 🟠 | Rendimiento | Búsqueda `ILIKE %term%` sin índice → full scan al crecer `noticia` | Pendiente (Fase 3) |
| [H-10](hallazgos.md#h-10) | 🟡 | Seguridad | Sin CORS configurado (rompe frontend browser) ni control explícito | No aplica hoy* |
| [H-11](hallazgos.md#h-11) | 🟡 | Robustez | Sin manejador global de excepciones ni respuestas de error uniformes | Pendiente (Fase 2) |
| [H-12](hallazgos.md#h-12) | 🟡 | Operación | Sin endpoint de health/readiness para monitoreo y Nginx | ✅ Resuelto |
| [H-13](hallazgos.md#h-13) | 🟡 | Rendimiento | Pool de conexiones sin `pool_pre_ping`/tuning → conexiones muertas tras restart de DB | ✅ Resuelto |
| [H-14](hallazgos.md#h-14) | 🟡 | Concurrencia | `POST /scraper/run` sin lock → corridas de scraping solapadas | Pendiente (Fase 2) |
| [H-15](hallazgos.md#h-15) | 🟡 | Rendimiento | Paginación por `OFFSET` (degrada en páginas profundas) | Pendiente (Fase 3) |
| [H-16](hallazgos.md#h-16) | 🟡 | Observabilidad | Sin logging de requests / correlation-id en la API | Pendiente (Fase 2)** |
| [H-17](hallazgos.md#h-17) | 🟡 | Higiene | `config.API_KEY` en desuso (dead config) y confusión con la key por-usuario | ✅ Resuelto |
| [H-18](hallazgos.md#h-18) | 🟡 | Docs | `docs/API.md` desactualizado: orden de `/noticias` ahora es `id DESC`, no `date_preview` | ✅ Resuelto |

\* El frontend consume esta API server-to-server a través de un proxy Django (nunca desde el navegador del usuario final), así que CORS no aplica en el despliegue actual. Queda documentado por si en el futuro un cliente browser llama directo a un dominio distinto.

\*\* Ya existe logging de aplicación (`logs/api.log`, agregado al resolver H-01/T1.1 — el proceso de la API no tenía *ningún* logging configurado, ni siquiera para errores). Falta el middleware de request-id/latencia por request, que sigue en Fase 2.

Detalle completo en [`hallazgos.md`](hallazgos.md). Plan de ejecución en [`ROADMAP.md`](ROADMAP.md).
