from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import text
from config import *


DATABASE_URL = f"postgresql://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"

engine = create_engine(DATABASE_URL, echo=False)


def _run_schema_updates() -> None:
    """Aplica cambios simples de esquema sin requerir recrear la base."""
    with engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE noticia ADD COLUMN IF NOT EXISTS excerpt TEXT")
        )
        connection.execute(
            text(
                """
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'usuarionoticiavista_noticia_id_fkey'
                    ) THEN
                        ALTER TABLE usuarionoticiavista
                        DROP CONSTRAINT usuarionoticiavista_noticia_id_fkey;
                    END IF;

                    ALTER TABLE usuarionoticiavista
                    ADD CONSTRAINT usuarionoticiavista_noticia_id_fkey
                    FOREIGN KEY (noticia_id)
                    REFERENCES noticia(id)
                    ON DELETE CASCADE;
                EXCEPTION
                    WHEN duplicate_object THEN NULL;
                END $$;
                """
            )
        )


def create_db():
    """Crea tablas y aplica ajustes de esquema si no existen."""
    SQLModel.metadata.create_all(engine)
    _run_schema_updates()


def get_session():
    with Session(engine) as session:
        yield session
