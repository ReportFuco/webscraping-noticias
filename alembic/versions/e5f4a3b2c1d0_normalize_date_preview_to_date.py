"""normalize date_preview to DATE type, drop published_date

Revision ID: e5f4a3b2c1d0
Revises: cbcd0d416fee
Create Date: 2026-05-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e5f4a3b2c1d0'
down_revision: Union[str, Sequence[str], None] = '8ab361bce1ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop NOT NULL before changing type: some rows may not match any known
    # format and will legitimately become NULL (the model uses Optional[date]).
    op.execute("ALTER TABLE noticia ALTER COLUMN date_preview DROP NOT NULL")

    # Convert date_preview TEXT → DATE.
    # Priority: use published_date (already parsed) where available;
    # otherwise attempt to parse the text value.
    op.execute("""
        ALTER TABLE noticia
        ALTER COLUMN date_preview TYPE DATE
        USING (
            CASE
                WHEN published_date IS NOT NULL
                    THEN published_date
                WHEN date_preview ~ '^[0-9]{1,2}/[0-9]{1,2}/[0-9]{4}$'
                    AND SPLIT_PART(date_preview, '/', 2)::int BETWEEN 1 AND 12
                    THEN TO_DATE(
                            LPAD(SPLIT_PART(date_preview, '/', 1), 2, '0') || '/' ||
                            LPAD(SPLIT_PART(date_preview, '/', 2), 2, '0') || '/' ||
                            SPLIT_PART(date_preview, '/', 3),
                            'DD/MM/YYYY'
                         )
                WHEN date_preview ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}'
                    THEN SUBSTRING(date_preview, 1, 10)::date
                WHEN date_preview ~ '^[0-9]{2}-[0-9]{2}-[0-9]{4}$'
                    AND SPLIT_PART(date_preview, '-', 2)::int BETWEEN 1 AND 12
                    THEN TO_DATE(date_preview, 'DD-MM-YYYY')
                ELSE NULL
            END
        )
    """)

    op.create_index('ix_noticia_date_preview', 'noticia', ['date_preview'])

    # Drop the now-redundant published_date column
    op.drop_index('ix_noticia_published_date', table_name='noticia')
    op.drop_column('noticia', 'published_date')


def downgrade() -> None:
    op.add_column('noticia', sa.Column('published_date', sa.Date(), nullable=True))
    op.create_index('ix_noticia_published_date', 'noticia', ['published_date'])

    op.execute("""
        UPDATE noticia
        SET published_date = date_preview
        WHERE date_preview IS NOT NULL
    """)

    op.execute("""
        ALTER TABLE noticia
        ALTER COLUMN date_preview TYPE TEXT
        USING (
            CASE
                WHEN date_preview IS NOT NULL
                    THEN TO_CHAR(date_preview, 'DD/MM/YYYY')
                ELSE NULL
            END
        )
    """)

    op.drop_index('ix_noticia_date_preview', table_name='noticia')
