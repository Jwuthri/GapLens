"""Initial migration: create reviews, analyses, and complaint_clusters tables

Revision ID: 6bee9faef024
Revises: 
Create Date: 2025-08-17 23:38:04.564764

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '6bee9faef024'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types using raw SQL to avoid SQLAlchemy caching issues
    connection = op.get_bind()
    
    # Create platform enum if it doesn't exist
    connection.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE platform AS ENUM ('google_play', 'app_store');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))
    
    # Create analysisstatus enum if it doesn't exist
    connection.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE analysisstatus AS ENUM ('pending', 'processing', 'completed', 'failed');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))
    
    # Get the enum types for table creation (these should now exist)
    platform_enum = postgresql.ENUM('google_play', 'app_store', name='platform', create_type=False)
    analysis_status_enum = postgresql.ENUM('pending', 'processing', 'completed', 'failed', name='analysisstatus', create_type=False)
    
    # Create reviews table
    op.create_table('reviews',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('app_id', sa.String(), nullable=False),
        sa.Column('platform', platform_enum, nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('review_date', sa.DateTime(), nullable=False),
        sa.Column('locale', sa.String(), nullable=True),
        sa.Column('processed', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reviews_id'), 'reviews', ['id'], unique=False)
    op.create_index(op.f('ix_reviews_app_id'), 'reviews', ['app_id'], unique=False)
    
    # Create analyses table
    op.create_table('analyses',
        sa.Column('id', postgresql.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('app_id', sa.String(), nullable=False),
        sa.Column('platform', platform_enum, nullable=False),
        sa.Column('status', analysis_status_enum, nullable=False, default='pending'),
        sa.Column('total_reviews', sa.Integer(), nullable=True),
        sa.Column('negative_reviews', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_analyses_id'), 'analyses', ['id'], unique=False)
    op.create_index(op.f('ix_analyses_app_id'), 'analyses', ['app_id'], unique=False)
    
    # Create complaint_clusters table
    op.create_table('complaint_clusters',
        sa.Column('id', postgresql.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('analysis_id', postgresql.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('review_count', sa.Integer(), nullable=False),
        sa.Column('percentage', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('recency_score', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('sample_reviews', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('keywords', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['analysis_id'], ['analyses.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_complaint_clusters_id'), 'complaint_clusters', ['id'], unique=False)
    op.create_index(op.f('ix_complaint_clusters_analysis_id'), 'complaint_clusters', ['analysis_id'], unique=False)


def downgrade() -> None:
    # Drop tables
    op.drop_table('complaint_clusters')
    op.drop_table('analyses')
    op.drop_table('reviews')
    
    # Drop enum types with checkfirst=True
    analysis_status_enum = postgresql.ENUM('pending', 'processing', 'completed', 'failed', name='analysisstatus')
    analysis_status_enum.drop(op.get_bind(), checkfirst=True)
    
    platform_enum = postgresql.ENUM('google_play', 'app_store', name='platform')
    platform_enum.drop(op.get_bind(), checkfirst=True)
