"""Update platform enum with all platform values

Revision ID: c014b027636b
Revises: 802ccd5fa22f
Create Date: 2025-08-24 02:57:45.623950

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c014b027636b'
down_revision: Union[str, None] = '802ccd5fa22f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Convert enum columns to VARCHAR to support all platform values
    op.alter_column('analyses', 'platform',
               existing_type=postgresql.ENUM('google_play', 'app_store', name='platform'),
               type_=sa.String(),
               existing_nullable=True)
    op.alter_column('analyses', 'status',
               existing_type=postgresql.ENUM('pending', 'processing', 'completed', 'failed', name='analysisstatus'),
               type_=sa.String(),
               existing_nullable=False)
    op.alter_column('reviews', 'platform',
               existing_type=postgresql.ENUM('google_play', 'app_store', name='platform'),
               type_=sa.String(),
               existing_nullable=False)
    
    # Drop the old enum types
    op.execute("DROP TYPE IF EXISTS platform CASCADE")
    op.execute("DROP TYPE IF EXISTS analysisstatus CASCADE")


def downgrade() -> None:
    # Recreate the old enum types
    op.execute("CREATE TYPE platform AS ENUM ('google_play', 'app_store')")
    op.execute("CREATE TYPE analysisstatus AS ENUM ('pending', 'processing', 'completed', 'failed')")
    
    # Convert back to enum columns
    op.alter_column('reviews', 'platform',
               existing_type=sa.String(),
               type_=postgresql.ENUM('google_play', 'app_store', name='platform'),
               existing_nullable=False)
    op.alter_column('analyses', 'status',
               existing_type=sa.String(),
               type_=postgresql.ENUM('pending', 'processing', 'completed', 'failed', name='analysisstatus'),
               existing_nullable=False)
    op.alter_column('analyses', 'platform',
               existing_type=sa.String(),
               type_=postgresql.ENUM('google_play', 'app_store', name='platform'),
               existing_nullable=True)
