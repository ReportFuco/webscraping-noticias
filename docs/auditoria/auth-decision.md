# Decisión de autenticación (ADR)

> **Estado:** ✅ Implementada por completo (T1.1, T1.2, T1.3). Registro abierto con verificación de email (decisión tomada por el owner); tabla `api_key` + `/me/api-keys` en producción, verificado end-to-end. Detalle de ejecución en `ROADMAP.md`.
> **Leer esto antes de tocar cualquier cosa de auth.** Ver hallazgos [H-01](hallazgos.md#h-01), [H-02](hallazgos.md#h-02), [H-03](hallazgos.md#h-03), [H-05](hallazgos.md#h-05), [H-06](hallazgos.md#h-06), [H-17](hallazgos.md#h-17).

**Caso de uso confirmado por el owner:** los usuarios se autentican con **JWT** (usuario/contraseña) y desde su sesión pueden **crear y dar de baja sus propias API keys**, que luego usan para llamar a `/noticias` (y demás recursos) de forma programática. Es decir, relación **1 usuario → N API keys**, gestionables (no una key fija por usuario como hoy).

## Contexto: qué hay hoy

Conviven **dos** mecanismos y la línea entre ambos es difusa:

| Mecanismo | Dónde se usa | Cómo funciona |
|---|---|---|
| **JWT** (`fastapi-users`) | `/auth/*`, `/users/*` | Login → Bearer token de 30 días. Firma con `JWT_SECRET`. |
| **API Key** (`X-API-Key`) | `/noticias/*`, `/scraper/*`, `/webhooks/*` | Header → busca `api_user.api_key` activo en DB. |

Puntos de fricción:

- El **JWT solo sirve para gestionar la cuenta** (login, ver/editar perfil, recuperar la api_key). No protege ningún recurso de negocio.
- Los recursos de negocio (incluido `/scraper` y `/webhooks`, que son de superuser) se protegen con **API Key**, no con JWT — pese a que `docs/API.md` dice lo contrario (H-05).
- El **registro es público** (H-01): cualquiera obtiene una api_key con acceso de lectura total.
- Hay un `config.API_KEY` global **sin uso** que confunde (H-17).

## Modelo recomendado

**Mantener los dos mecanismos, con roles claros y separados:**

1. **JWT = identidad de humanos.** Login, perfil, y **gestión de API keys propias** (crear/listar/revocar). Sesión de 30 días vía `fastapi-users`.
2. **API Key = credencial de servicios / integraciones.** Acceso programático a `/noticias` y demás recursos de negocio. Una cuenta puede tener **varias** keys activas simultáneamente (una por integración/agente, revocables sin afectar al resto).
3. **Superuser = operaciones sensibles.** `/scraper/run`, `/webhooks/*` y `PATCH /noticias` (H-06) requieren que el usuario dueño de la key (o de la sesión JWT) sea superuser.

Esta separación es estándar (JWT para sesiones de usuario, API keys para integraciones) y es exactamente lo que el owner pidió: *"usuarios se autentican y levantan/dan de baja API keys para usar la API"*.

### Diseño: tabla `api_key` (reemplaza la columna fija en `user`)

Hoy `models/user.py` tiene una única columna `api_key` generada al registrarse — no alcanza para múltiples keys revocables. Se necesita una tabla nueva:

```python
class ApiKey(Base):
    __tablename__ = "api_key"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("api_user.id", ondelete="CASCADE"), index=True)
    name: Mapped[str]                      # etiqueta libre, ej. "n8n-prod"
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # sha256(key)
    key_prefix: Mapped[str] = mapped_column(String(8))  # primeros chars, para reconocerla en listados sin exponer la key completa
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    last_used_at: Mapped[Optional[datetime]]
```

- La key en claro (`secrets.token_urlsafe(32)`) se muestra **solo una vez**, en la respuesta de `POST /me/api-keys`. Después solo existe su hash en DB.
- `verify_api_key` (`api/deps.py`) pasa a: hashear el header recibido → buscar en `api_key` por `key_hash` + `is_active` → cargar el `User` asociado (join) → actualizar `last_used_at` (async, no bloqueante).
- `is_superuser` sigue viviendo en `User`, no en `ApiKey` — todas las keys de un superuser heredan ese privilegio.

### Endpoints nuevos (protegidos por JWT, `current_active_user` de `fastapi-users`)

| Endpoint | Qué hace |
|---|---|
| `GET /me/api-keys` | Lista las keys del usuario logueado: `id`, `name`, `key_prefix`, `is_active`, `created_at`, `last_used_at`. **Nunca** la key completa. |
| `POST /me/api-keys` | Crea una key nueva (`body: {name}`). Responde `{id, name, api_key: "<key-en-claro>", created_at}` — única vez que se ve completa. |
| `DELETE /me/api-keys/{id}` | Da de baja (soft: `is_active=False`, o hard delete — a definir). `404` si no es del usuario logueado. |

Notas de implementación:
- Estos endpoints van bajo `/me/api-keys`, montados junto a los routers de `fastapi-users` en `api/app.py`, usando `Depends(current_active_user)` (ya existe en `api/users.py:42`, hoy sin uso — este es su primer consumidor real).
- Migración Alembic para crear `api_key` + migrar las keys existentes de `api_user.api_key` (una fila `ApiKey` por usuario, marcada `name="legacy"`) para no invalidar integraciones actuales de un día para otro. Luego, en un paso posterior, se puede eliminar la columna `api_user.api_key`.

### Cambios concretos que implica (checklist ejecutable en `ROADMAP.md`)

- [x] **Cerrar/gatear el registro público** (H-01): abierto + verificación de email obligatoria. Hecho en T1.1.
- [x] **Fail-fast de secretos** (H-02): hecho en Fase 0.
- [x] **Tabla `api_key` + endpoints `/me/api-keys`** (H-03, más el requerimiento de múltiples keys): hecho en T1.3, verificado end-to-end.
- [x] **`PATCH /noticias` → superuser** (H-06): hecho en T1.2.
- [x] **Eliminar `config.API_KEY`** global (H-17): hecho en Fase 0.
- [x] **Alinear la doc** con el código (H-05, H-18): hecho en Fase 0 y T1.1/T1.3.

## Alternativas consideradas (y por qué no)

- **Solo API Key (eliminar JWT).** Más simple, pero se pierde el flujo de gestión de cuenta/recuperación y el `fastapi-users` ya integrado; no aporta cerrar esa puerta.
- **Solo JWT (eliminar API Key).** Malo para integraciones máquina-a-máquina: obliga a re-login cada 30 días y a manejar refresh en clientes que solo quieren un token estable.
- **OAuth2 / proveedor externo.** Sobredimensionado para el tamaño actual; reconsiderar solo si aparece multi-tenant o SSO.

## Decisiones tomadas (registro histórico)

1. **Registro:** abierto con verificación de email obligatoria. Decisión del owner (2026-07-01). Implementado en T1.1: `POST /auth/register` sigue público, pero `verify_api_key` rechaza con `403` si la cuenta no está `is_verified`.
2. **Revocar una key:** soft-delete (`is_active=False`). Se usó el default sugerido; permite ver el historial de keys usadas en `GET /me/api-keys`.
3. **Migración de api_key existentes:** sí, automática — cada `api_user.api_key` se copió como una fila `ApiKey` con `name="legacy"` en la misma migración que crea la tabla (`b4a39c468953`). No hubo corte de servicio para las integraciones vigentes.

## Limitación conocida (no bloquea, pendiente de otra pasada)

El token de verificación de email no se envía automáticamente (no hay servicio de email ni WhatsApp conectado a ese flujo todavía) — queda logueado en `logs/api.log` para entrega manual. Conectar un canal real (SMTP o reusar Evolution API) es follow-up, no bloquea el uso actual.
