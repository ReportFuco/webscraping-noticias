# Roadmap de mejora — API

Plan de ejecución priorizado por **impacto / esfuerzo**. Cada tarea referencia su hallazgo en [`hallazgos.md`](hallazgos.md) y tiene un **criterio de aceptación** verificable.

Convención: marca `[x]` al completar. Tras cambios de API → `sudo systemctl restart noticias-api`.

Orden recomendado: **Fase 0 → 1 → 2 → 3**. La Fase 1 depende de confirmar `auth-decision.md`.

---

## Fase 0 — Quick wins (bajo riesgo, alto valor inmediato)

Se pueden hacer ya, sin decisiones de producto de por medio.

- [x] **T0.1 — Fail-fast de secretos** · H-02 · S
  - Validar en arranque que `JWT_SECRET` existe y ≥32 chars; abortar si no. (Idealmente migrar `config.py` a Pydantic `BaseSettings`.)
  - **Aceptación:** con `JWT_SECRET=""` la app **no** arranca y loguea el motivo.
  - **Hecho:** validación en `api/users.py` (no en `config.py`, que también importa el pipeline de scraping y no debe depender de `JWT_SECRET`).

- [x] **T0.2 — Endpoint de health/readiness** · H-12 · S
  - `GET /health` (sin auth, sin DB) y `GET /ready` (`SELECT 1`). Excluir de auth.
  - **Aceptación:** `curl /health` → `200` sin credenciales; `/ready` → `200` con DB arriba, `503` con DB caída.
  - **Hecho:** `src/api/routers/health.py`, verificado con curl.

- [x] **T0.3 — Tuning del pool de conexiones** · H-13 · S
  - `pool_pre_ping=True`, `pool_recycle=1800` en ambos engines de `src/database.py`.
  - **Aceptación:** tras reiniciar Postgres, el siguiente request a la API responde OK sin error de conexión muerta.
  - **Hecho.**

- [x] **T0.4 — Sacar migraciones del runtime** · H-08 · S
  - Quitar `create_db()` del `lifespan`; correr `alembic upgrade head` como `ExecStartPre` del service (o paso de deploy).
  - **Aceptación:** arrancar 2 workers no dispara 2 migraciones; el deploy documenta el paso de upgrade.
  - **Hecho:** `ExecStartPre` agregado en `/etc/systemd/system/noticias-api.service` (fuera del repo git). Verificado: migración corre una vez antes de levantar los 2 workers.

- [x] **T0.5 — Actualizar documentación** · H-05, H-18 · S
  - `docs/API.md`: orden de `/noticias` = `id DESC`; auth de `/scraper` = API Key de superuser (no JWT).
  - **Aceptación:** la doc coincide con el código verificado en `src/api/routers/`.
  - **Hecho**, más agregadas secciones que faltaban: `/health`, `/ready`, `/webhooks`, `/auth/verify`.

- [x] **T0.6 — Limpiar `config.API_KEY` en desuso** · H-17 · S
  - Eliminar de `config.py`, `.env`, `.env.example` (o documentar si tiene un uso real que se me escapó).
  - **Aceptación:** grep de `API_KEY` no aparece salvo donde se use de verdad.
  - **Hecho.**

---

## Fase 1 — Endurecer autenticación

> Decisión confirmada en `auth-decision.md`: registro **abierto con verificación de email**; usuarios gestionan múltiples API keys vía JWT.

- [x] **T1.1 — Registro abierto con verificación de email** · H-01 · M
  - `POST /auth/register` sigue público, pero la cuenta nace `is_verified=false`; `verify_api_key` (`api/deps.py`) ahora exige `is_verified=True` → `403` si no.
  - `UserManager.on_after_register` dispara `request_verify()` automáticamente; el token queda logueado en `logs/api.log` (**no hay envío de email/WhatsApp automático todavía** — limitación conocida, ver nota abajo).
  - Se montó `fastapi_users_app.get_verify_router` → `POST /auth/request-verify-token` y `POST /auth/verify`.
  - Cuentas existentes (`test@test.com`, la del owner) migradas a `is_verified=true` para no romper acceso vigente.
  - **Bug encontrado y corregido en el camino:** el proceso de la API no tenía logging configurado (nada se veía ni en `api_error.log` ni en ningún lado); se agregó `setup_logging()` con archivo dedicado `logs/api.log` en `api/app.py`.
  - **Aceptación:** verificado end-to-end — registro → `403` sin verificar → `POST /auth/verify` con el token del log → `200` verificado → API key funciona.
  - **Pendiente de seguimiento (no bloquea):** conectar entrega real del token (email o WhatsApp vía Evolution API) en vez de depender de logs + entrega manual.

- [x] **T1.2 — `PATCH /noticias/{id}` solo superuser** · H-06 · S
  - Añadir `Depends(verify_superuser)` al endpoint.
  - **Aceptación:** api_key de usuario normal → `403`; superuser → `200`.
  - **Hecho y verificado.**

- [x] **T1.3 — Múltiples API keys gestionables por usuario** · H-03 · M
  - Reemplaza el hallazgo original ("hashear la key única") por el diseño completo de `auth-decision.md`: tabla `api_key` (1 usuario → N keys), keys hasheadas desde el diseño, endpoints `GET/POST/DELETE /me/api-keys` protegidos por JWT.
  - Migrar las keys actuales de `api_user.api_key` como una `ApiKey` `name="legacy"` para no cortar acceso vigente.
  - **Aceptación:** usuario logueado por JWT puede crear una key nueva (ve el secreto una sola vez), listarlas (sin exponer el secreto) y revocar una sin afectar las demás; `verify_api_key` valida por hash contra la tabla nueva.
  - **Hecho.** Migración `b4a39c468953_add_api_key_table.py` (tabla + migración de datos legacy). Verificado end-to-end: crear key → usar → listar (sin secreto) → revocar → confirmar `401`. Las 2 keys legacy (owner + test) migradas y funcionando sin corte de servicio.
  - **Bug encontrado y corregido en el camino:** import circular real entre `fastapi_users` y `fastapi_users_db_sqlalchemy==7.0.0` — si algo importa `fastapi_users_db_sqlalchemy.generics` antes que `fastapi_users.db`, este último queda con `SQLAlchemyBaseUserTableUUID` roto (ImportError silenciado por la librería) para el resto del proceso. Se agregó un `import fastapi_users.db` explícito como primera línea de `models/__init__.py` para forzar el orden correcto. Se descubrió con `alembic revision --autogenerate`, **antes** de tocar el servicio en producción.
  - **Cambio de contrato de API:** `UserRead` (y la respuesta de `POST /auth/register`) ya no incluye `api_key` — ese campo quedó obsoleto, reemplazado por `/me/api-keys`. `docs/API.md` actualizado.
  - **Pendiente de seguimiento (no bloquea, queda para otra pasada):** eliminar la columna `api_user.api_key` en una migración futura (se dejó por compatibilidad de esquema, ya no se usa para auth).

---

## Fase 2 — Defensas de borde

- [ ] **T2.1 — Rate limiting** · H-04 · M
  - `slowapi` (o `limit_req` en Nginx). Estricto en `/auth/*`, laxo en `/noticias`.
  - **Aceptación:** exceder el límite en `/auth/jwt/login` devuelve `429`.

- [ ] **T2.2 — Manejador global de errores + request-id** · H-11, H-16 · S
  - Handlers para `RequestValidationError`, `IntegrityError`, `Exception` con shape uniforme; middleware que asigna `X-Request-ID` y loguea método/ruta/status/latencia.
  - **Aceptación:** un error no controlado devuelve JSON uniforme con `request_id`; el log correlaciona ese id.

- [ ] **T2.3 — CORS explícito** · H-10 · S
  - `CORSMiddleware` con allowlist de orígenes (sin `*` con credenciales). Documentar.
  - **Aceptación:** origen permitido pasa preflight; origen no listado es rechazado.

- [ ] **T2.4 — Lock de scraping** · H-14 · M
  - `pg_advisory_lock` en `procesar_noticias` o rechazar si hay `ScrapeRun` "running" reciente (`409`).
  - **Aceptación:** dos `POST /scraper/run` seguidos no lanzan dos pipelines concurrentes.

---

## Fase 3 — Rendimiento y webhooks

- [ ] **T3.1 — Índice para búsqueda de texto** · H-09 · M
  - Corto plazo: `pg_trgm` + índice GIN sobre `title`/`excerpt`. Mejor: `tsvector` + `unaccent`. Vía migración Alembic.
  - **Aceptación:** `EXPLAIN` de una búsqueda `?buscar=...` usa el índice (no seq scan) en una tabla con volumen.

- [ ] **T3.2 — Endurecer webhooks** · H-07 · L
  - Firma HMAC del payload (`X-Webhook-Signature`), allowlist de dominios / bloqueo de IPs privadas (anti-SSRF), reintentos con backoff.
  - **Aceptación:** el receptor puede validar la firma; una URL a IP privada es rechazada al crear/disparar; un fallo transitorio se reintenta.

- [ ] **T3.3 — Keyset pagination opcional** · H-15 · M
  - Cursor por `id` además del `offset` actual.
  - **Aceptación:** iterar con cursor no degrada en páginas profundas; el `offset` clásico sigue disponible.

---

## Cómo validar cambios de API

```bash
# Reiniciar tras cambios (Nginx NO se toca)
sudo systemctl restart noticias-api
sudo systemctl status noticias-api --no-pager
journalctl -u noticias-api -f

# Smoke test rápido
curl -s http://127.0.0.1:8010/health            # tras T0.2
curl -s -H "X-API-Key: $KEY" http://127.0.0.1:8010/noticias | head
```

## Dependencias sugeridas a añadir (`requirements.txt`)

- `slowapi` (T2.1)
- `pydantic-settings` (T0.1, si se migra config a `BaseSettings`)
- `pg_trgm` / `unaccent` son extensiones de Postgres (no pip): habilitar vía migración (T3.1).
