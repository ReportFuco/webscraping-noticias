# Catálogo de hallazgos

Cada hallazgo tiene: **evidencia** (`archivo:línea`), **impacto**, **remediación propuesta** y **esfuerzo** estimado (S ≤ 1h, M ≤ media jornada, L ≥ 1 jornada).

Severidad: 🔴 Alta · 🟠 Media · 🟡 Baja

---

## H-01
### 🔴 Registro público otorga acceso a toda la data · Auth

> **Estado: resuelto (T1.1).** El registro sigue abierto (decisión del owner) pero ahora exige verificación de email antes de que la api_key sirva para nada: `verify_api_key` rechaza con `403` si `is_verified=False`. Ver `ROADMAP.md` T1.1 para el detalle y la limitación conocida (entrega del token es manual por ahora, no hay email/WhatsApp automático).

**Evidencia:** `src/api/app.py:32-36` monta `get_register_router` sin gating. Cualquiera puede `POST /auth/register`, recibir una `api_key` (`src/api/users.py:46-48`, `src/models/user.py:12-18`) y con ella:
- Leer **todas** las noticias (`GET /noticias`, router protegido solo por `verify_api_key`, `src/api/routers/noticias.py:14`).
- Editar título/excerpt de **cualquier** noticia (`PATCH /noticias/{id}`, ver H-06).

**Impacto:** No hay barrera entre "internet" y la base de datos de noticias. Un registro anónimo = acceso de lectura total + escritura editorial. Si el producto es de pago o privado, esto lo rompe.

**Remediación:**
- Decidir el modelo de acceso (ver `auth-decision.md`).
- Opción A: deshabilitar el registro público y crear usuarios/keys por CLI/admin.
- Opción B: mantener registro pero exigir verificación de email (`is_verified`) y que la API key **no** habilite lectura hasta aprobación manual.
- Opción C: gating por invitación (código de registro en `.env`).

**Esfuerzo:** M

---

## H-02
### 🔴 `JWT_SECRET` / `API_KEY` con default vacío · Auth

> **Estado: resuelto (T0.1).** Validación fail-fast agregada en `api/users.py` (no en `config.py`, que también usa el pipeline de scraping sin depender de `JWT_SECRET`). `API_KEY` global eliminado (ver H-17).

**Evidencia:** `src/config.py:49-50` → `getenv("API_KEY", "")` y `getenv("JWT_SECRET", "")`. El secreto JWT se usa en `src/api/users.py:19-20,31` para firmar/validar tokens. Si la env var falta, arranca con `secret=""`.

**Impacto:** Con `JWT_SECRET=""` los tokens son **forjables** por cualquiera que conozca el algoritmo (secreto conocido/trivial). Falla en silencio: la app levanta igual.

**Remediación:**
- Validar en el arranque (`fail-fast`): si `JWT_SECRET` está vacío o < 32 chars → `raise RuntimeError`. Idealmente en un `config.py` con Pydantic `BaseSettings` que valide tipos y obligatoriedad.
- Rotar `JWT_SECRET` actual (invalida sesiones vigentes; aceptable).
- Eliminar `API_KEY` global si no se usa (ver H-17).

**Esfuerzo:** S

---

## H-03
### 🔴 API keys y secretos de webhook en texto plano · Auth

> **Estado: parcialmente resuelto (T1.3).** API keys: reemplazadas por completo por el diseño de `auth-decision.md` — tabla `api_key` (1 usuario → N keys), guardadas como `sha256(key)`, el valor en claro solo se muestra una vez al crearla (`POST /me/api-keys`). Keys legacy migradas y ya hasheadas. **Pendiente:** el secreto de webhook (`WebhookSubscriptor.secret`) sigue en texto plano — eso es H-07 (Fase 3), no se tocó en esta pasada.

**Evidencia:**
- `src/models/user.py:12-18`: `api_key` se guarda tal cual (`secrets.token_urlsafe(32)`), columna `String(64)`.
- `src/models/webhook.py:14`: `secret` en texto plano; `src/services/webhook_dispatcher.py:48` lo envía en header `X-Webhook-Secret`.

**Impacto:** Una fuga de la DB (backup, dump, acceso de lectura) expone credenciales usables directamente. Las API keys son *bearer credentials*: quien las lee, las usa.

**Remediación:**
- API keys: almacenar solo un **hash** (SHA-256) y comparar por hash en `verify_api_key`. Mostrar la key en claro **solo una vez** al crearla. Requiere índice sobre el hash.
- Webhook secret: usarlo como clave HMAC (ver H-07) en vez de enviarlo; guardarlo cifrado o al menos fuera de logs.

**Esfuerzo:** M

---

## H-04
### 🟠 Sin rate limiting · Seguridad

**Evidencia:** No hay `slowapi`, middleware ni límites en `src/api/**` (grep sin resultados). `POST /auth/jwt/login` y `POST /auth/register` quedan abiertos a fuerza bruta / abuso.

**Impacto:** Fuerza bruta de contraseñas, enumeración, y agotamiento de recursos (cada request de `/noticias` hace ≥2 queries). Login sin throttling es el vector más obvio.

**Remediación:**
- Añadir `slowapi` (o límite en Nginx) con límites por IP: estricto en `/auth/*` (p.ej. 5/min), laxo en `/noticias` (p.ej. 60/min).
- Alternativa mínima: `limit_req` en Nginx para `/auth/`.

**Esfuerzo:** M

---

## H-05
### 🟠 Discrepancia doc↔código en `/scraper` · Docs/Auth

> **Estado: resuelto (T0.5).** `docs/API.md` corregido para reflejar que `/scraper` usa `X-API-Key` de superuser, no JWT.

**Evidencia:** `docs/API.md:226` afirma *"Requiere autenticación JWT ... is_superuser=true"*. El código (`src/api/routers/scraper.py:7,13,17`) usa `verify_superuser`, que depende de `verify_api_key` (`src/api/deps.py:27-30`). Es decir: **API Key de un superuser**, no JWT.

**Impacto:** Confusión para consumidores e integraciones; un agente que siga la doc mandará `Authorization: Bearer` y recibirá 401. Señal de que la estrategia de auth no está consolidada.

**Remediación:** Definir la estrategia (ver `auth-decision.md`) y luego alinear doc y código. Corregir `docs/API.md`.

**Esfuerzo:** S

---

## H-06
### 🟠 `PATCH /noticias/{id}` abierto a cualquier usuario · Auth

> **Estado: resuelto (T1.2).** Se agregó `dependencies=[Depends(verify_superuser)]` al endpoint. Verificado: usuario normal → `403`; superuser → `200`; `GET` sigue abierto a cualquier usuario con key válida y verificada.

**Evidencia:** `src/api/routers/noticias.py:14` aplica `verify_api_key` a todo el router, pero `patch_noticia` (`:54-68`) **no** exige superuser. Cualquier holder de API key puede reescribir `title`/`excerpt` de cualquier noticia.

**Impacto:** Escritura editorial sin control. Combinado con H-01 (registro público), cualquiera podría alterar contenido servido a los usuarios de WhatsApp.

**Remediación:** Exigir `verify_superuser` en `PATCH` (y evaluar separar permisos de lectura vs escritura). Si se quiere escritura por terceros, registrar auditoría (quién editó qué).

**Esfuerzo:** S

---

## H-07
### 🟠 Webhooks: SSRF + secreto plano + sin reintentos · Seguridad

**Evidencia:** `src/services/webhook_dispatcher.py:45-50` hace `POST` a `sub.url` (definida vía `POST /webhooks`, `src/api/routers/webhooks.py:27-33`) con el secreto **en un header** (no firma). Sin validación de destino, sin reintentos, sin backoff.

**Impacto:**
- **SSRF:** un superuser (o quien escale) puede apuntar la URL a `http://169.254.169.254/...` o servicios internos; el servidor hará la request desde dentro de la red.
- **Sin integridad:** enviar el secreto plano no prueba que el payload no fue alterado; un HMAC del cuerpo sí.
- **Sin reintentos:** un webhook caído pierde el evento silenciosamente (`:52-53` solo loguea).

**Remediación:**
- Firmar el payload: `X-Webhook-Signature: sha256=HMAC(secret, body)`; el receptor verifica.
- Validar/allowlist de dominios de destino; bloquear IPs privadas/loopback/link-local.
- Reintentos con backoff (o cola simple + tabla de intentos). Timeout ya existe (10s).

**Esfuerzo:** L

---

## H-08
### 🟠 Migraciones en cada worker al arrancar · Operación

> **Estado: resuelto (T0.4).** `create_db()` sacado del `lifespan`; `alembic upgrade head` corre como `ExecStartPre` en `noticias-api.service`, una sola vez antes de levantar los workers.

**Evidencia:** `src/api/app.py:10-13` corre `create_db()` en el `lifespan`; `src/database.py:22-26` hace `alembic upgrade head`. Con `gunicorn -w 2`, **ambos workers** ejecutan las migraciones al bootear casi en simultáneo.

**Impacto:** Race condition en el arranque: dos procesos aplicando el mismo `upgrade` pueden chocar (locks de DDL, errores intermitentes en deploy). También acopla el arranque de la API al estado de migración.

**Remediación:**
- Sacar la migración del runtime: correr `alembic upgrade head` como paso de deploy (ExecStartPre del service, o script de CI/CD), **no** en el `lifespan`.
- Si se mantiene en runtime, usar un lock de Postgres (`pg_advisory_lock`) para serializar.

**Esfuerzo:** S

---

## H-09
### 🟠 Búsqueda `ILIKE %term%` sin índice · Rendimiento

**Evidencia:** `src/api/routers/noticias.py:32-34` construye `%term%` y aplica `ILIKE` sobre `title` y `excerpt`. Un patrón con comodín inicial **no usa índice B-tree** → sequential scan.

**Impacto:** Hoy con pocas filas es imperceptible; con decenas/cientos de miles de noticias, cada búsqueda escanea toda la tabla (y encima se hace 2 veces: `count` + `select`).

**Remediación:**
- Corto plazo: índice GIN con `pg_trgm` (`CREATE EXTENSION pg_trgm; CREATE INDEX ... USING gin (title gin_trgm_ops)`), que sí acelera `ILIKE %...%`.
- Mejor: full-text search (`tsvector` + `to_tsquery`) con columna generada e índice GIN, y normalización de acentos (`unaccent`).

**Esfuerzo:** M

---

## H-10
### 🟡 Sin CORS configurado · Seguridad

**Evidencia:** No hay `CORSMiddleware` en `src/api/app.py`. 

**Impacto:** Un frontend en navegador (dominio distinto) no podrá consumir la API (preflight bloqueado). Inversamente, no hay una política explícita documentada. Hoy no rompe nada porque el consumo es server-to-server, pero es una decisión implícita.

**Remediación:** Añadir `CORSMiddleware` con allowlist explícita de orígenes (nunca `*` junto con credenciales). Documentar la decisión.

**Esfuerzo:** S

---

## H-11
### 🟡 Sin manejador global de excepciones · Robustez

**Evidencia:** No hay `@app.exception_handler` ni middleware de errores. Errores no controlados (p.ej. DB caída) devuelven el 500 genérico de Starlette y pueden filtrar trazas en logs sin formato uniforme.

**Impacto:** Respuestas de error inconsistentes; más difícil de consumir y de monitorear.

**Remediación:** Añadir handlers para `RequestValidationError`, `IntegrityError` y `Exception` genérica con un shape uniforme `{error, detail, request_id}`. No exponer trazas al cliente.

**Esfuerzo:** S

---

## H-12
### 🟡 Sin endpoint de health/readiness · Operación

> **Estado: resuelto (T0.2).** `src/api/routers/health.py`: `GET /health` y `GET /ready`, sin auth.

**Evidencia:** No existe `/health` ni `/ready`. Nginx y systemd no tienen un endpoint barato para chequear vida/DB.

**Impacto:** Monitoreo y health checks dependen de golpear endpoints reales (con auth). Deploys/rollbacks a ciegas.

**Remediación:** `GET /health` (proceso vivo, sin auth, sin DB) y `GET /ready` (hace `SELECT 1`). Excluir de auth y de rate limit.

**Esfuerzo:** S

---

## H-13
### 🟡 Pool de conexiones sin `pool_pre_ping`/tuning · Rendimiento

> **Estado: resuelto (T0.3).** `pool_pre_ping=True`, `pool_recycle=1800` en ambos engines.

**Evidencia:** `src/database.py:15-16` crea engines sin `pool_pre_ping`, `pool_size`, `max_overflow` ni `pool_recycle`.

**Impacto:** Tras un restart/timeout de Postgres, las conexiones del pool quedan muertas y el primer request falla (`OperationalError`) hasta reciclar. Bajo carga, el pool default puede quedar corto.

**Remediación:** `create_async_engine(..., pool_pre_ping=True, pool_recycle=1800, pool_size=..., max_overflow=...)`. Ajustar tamaños al número de workers.

**Esfuerzo:** S

---

## H-14
### 🟡 `POST /scraper/run` sin lock · Concurrencia

**Evidencia:** `src/api/routers/scraper.py:16-19` encola `procesar_noticias` como `BackgroundTask` sin verificar si ya hay una corrida en curso. `main.py` no toma ningún lock.

**Impacto:** Dos disparos seguidos (o solaparse con el cron) lanzan pipelines concurrentes: trabajo duplicado, contención en DB, entregas de WhatsApp duplicadas.

**Remediación:** Lock de aplicación: `pg_advisory_lock` al inicio de `procesar_noticias`, o verificar que no exista un `ScrapeRun` con `status="running"` reciente y responder `409` si lo hay.

**Esfuerzo:** M

---

## H-15
### 🟡 Paginación por `OFFSET` · Rendimiento

**Evidencia:** `src/api/routers/noticias.py:39` usa `.limit().offset()`. En páginas profundas Postgres igual recorre y descarta las filas saltadas.

**Impacto:** Menor hoy; degrada con tablas grandes y offsets altos. El `count` total también es costoso al crecer.

**Remediación:** Ofrecer keyset pagination (cursor por `id < last_id ORDER BY id DESC`) para clientes que iteran mucho. Mantener offset para UI simple.

**Esfuerzo:** M

---

## H-16
### 🟡 Sin logging de requests / correlation-id · Observabilidad

**Evidencia:** Solo `access.log` de gunicorn. No hay middleware que loguee método, ruta, status, latencia ni un `request_id` correlacionable con errores.

**Impacto:** Difícil depurar incidentes en producción o correlacionar un 500 con la request que lo causó.

**Remediación:** Middleware ligero que asigne `X-Request-ID`, mida latencia y loguee estructurado. Propagar el id a los error handlers (H-11).

**Esfuerzo:** S

---

## H-17
### 🟡 `config.API_KEY` en desuso · Higiene

> **Estado: resuelto (T0.6).** Eliminado de `config.py`, `.env`, `.env.example`.

**Evidencia:** `src/config.py:49` define `API_KEY` global, pero la autenticación real usa la `api_key` por-usuario de la tabla (`src/api/deps.py:18-23`). El global no se referencia en la capa API.

**Impacto:** Confusión: sugiere una API key única compartida que no existe. Riesgo de que alguien "la use" pensando que protege algo.

**Remediación:** Eliminar `API_KEY` de `config.py`/`.env`/`.env.example` si no se usa, o documentar su uso real. Consolidar la narrativa de auth (ver `auth-decision.md`).

**Esfuerzo:** S

---

## H-18
### 🟡 `docs/API.md` desactualizado · Docs

> **Estado: resuelto (T0.5).** Orden `id DESC` documentado; agregadas secciones faltantes (`/health`, `/ready`, `/webhooks`, `/auth/verify`).

**Evidencia:** `docs/API.md:127` dice que `/noticias` ordena por *"fecha de publicación descendente"*. Desde 2026-07-01 el orden es `Noticia.id.desc()` (`src/api/routers/noticias.py:39`) para evitar que noticias con `date_preview` nulo/antiguo suban al tope.

**Impacto:** Doc induce a error sobre el contrato de ordenamiento.

**Remediación:** Actualizar `docs/API.md` (orden por recencia de ingesta = `id DESC`). Revisar también la sección de auth de `/scraper` (H-05).

**Esfuerzo:** S
