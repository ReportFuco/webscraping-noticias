"""initial schema

Revision ID: aaf1d98822c0
Revises:
Create Date: 2026-05-18 16:32:50.810175

"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op


revision: str = 'aaf1d98822c0'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Agrega country con server_default para no romper filas existentes
    op.add_column('noticia', sa.Column(
        'country',
        sqlmodel.sql.sqltypes.AutoString(),
        nullable=False,
        server_default='CL',
    ))

    op.alter_column('noticia', 'excerpt',
                    existing_type=sa.TEXT(),
                    type_=sqlmodel.sql.sqltypes.AutoString(),
                    existing_nullable=True)

    op.create_index(op.f('ix_noticia_scrape_run_id'), 'noticia', ['scrape_run_id'], unique=False)

    op.drop_constraint('noticia_scrape_run_id_fkey', 'noticia', type_='foreignkey')
    op.create_foreign_key(
        'noticia_scrape_run_id_fkey', 'noticia', 'scraperun',
        ['scrape_run_id'], ['id'],
        ondelete='SET NULL',
    )

    op.alter_column('usuarionoticiavista', 'estado',
                    existing_type=sa.VARCHAR(length=50),
                    nullable=False,
                    existing_server_default=sa.text("'enviado'::character varying"))

    op.alter_column('usuarionoticiavista', 'detalle',
                    existing_type=sa.TEXT(),
                    type_=sqlmodel.sql.sqltypes.AutoString(),
                    existing_nullable=True)

    op.drop_constraint('usuarionoticiavista_noticia_id_fkey', 'usuarionoticiavista', type_='foreignkey')
    op.create_foreign_key(
        'usuarionoticiavista_noticia_id_fkey', 'usuarionoticiavista', 'noticia',
        ['noticia_id'], ['id'],
        ondelete='CASCADE',
    )


def downgrade() -> None:
    op.drop_constraint('usuarionoticiavista_noticia_id_fkey', 'usuarionoticiavista', type_='foreignkey')
    op.create_foreign_key(
        'usuarionoticiavista_noticia_id_fkey', 'usuarionoticiavista', 'noticia',
        ['noticia_id'], ['id'],
        ondelete='CASCADE',
    )

    op.alter_column('usuarionoticiavista', 'detalle',
                    existing_type=sqlmodel.sql.sqltypes.AutoString(),
                    type_=sa.TEXT(),
                    existing_nullable=True)

    op.alter_column('usuarionoticiavista', 'estado',
                    existing_type=sa.VARCHAR(length=50),
                    nullable=True,
                    existing_server_default=sa.text("'enviado'::character varying"))

    op.drop_constraint('noticia_scrape_run_id_fkey', 'noticia', type_='foreignkey')
    op.create_foreign_key(
        'noticia_scrape_run_id_fkey', 'noticia', 'scraperun',
        ['scrape_run_id'], ['id'],
        ondelete='SET NULL',
    )

    op.drop_index(op.f('ix_noticia_scrape_run_id'), table_name='noticia')

    op.alter_column('noticia', 'excerpt',
                    existing_type=sqlmodel.sql.sqltypes.AutoString(),
                    type_=sa.TEXT(),
                    existing_nullable=True)

    op.drop_column('noticia', 'country')
