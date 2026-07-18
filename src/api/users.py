import logging
import uuid

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin, schemas
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

import config as ENV
from database import get_async_session
from models.user import User

if len(ENV.JWT_SECRET) < 32:
    raise RuntimeError(
        "JWT_SECRET no está seteado o es demasiado corto (mínimo 32 caracteres). "
        "Define una variable de entorno JWT_SECRET robusta antes de arrancar la API."
    )

LOGGER = logging.getLogger(__name__)


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = ENV.JWT_SECRET
    verification_token_secret = ENV.JWT_SECRET

    async def on_after_register(self, user: User, request: Request | None = None) -> None:
        LOGGER.info("Usuario registrado email=%s id=%s (pendiente de verificación)", user.email, user.id)
        await self.request_verify(user, request)

    async def on_after_request_verify(self, user: User, token: str, request: Request | None = None) -> None:
        # No hay servicio de email configurado todavía (ver docs/auditoria/ROADMAP.md T1.1b):
        # el token queda logueado para que un admin lo entregue manualmente al usuario
        # mientras no exista envío automático.
        LOGGER.warning(
            "Token de verificación para email=%s: %s (entregar manualmente, no se envía email)",
            user.email, token,
        )

    async def on_after_verify(self, user: User, request: Request | None = None) -> None:
        LOGGER.info("Usuario verificado email=%s id=%s", user.email, user.id)


async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)


bearer_transport = BearerTransport(tokenUrl="/auth/jwt/login")


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=ENV.JWT_SECRET, lifetime_seconds=86400 * 30)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users_app = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

current_active_user = fastapi_users_app.current_user(active=True)
current_superuser = fastapi_users_app.current_user(active=True, superuser=True)


class UserRead(schemas.BaseUser[uuid.UUID]):
    pass


class UserCreate(schemas.BaseUserCreate):
    pass


class UserUpdate(schemas.BaseUserUpdate):
    pass
