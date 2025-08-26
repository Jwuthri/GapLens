"""Add performance indexes for optimized queries

Revision ID: performance_indexes
Revises: c014b027636b
Create Date: 2024-01-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'performance_indexes'
down_revision = 'c014b027636b'
branch_labels = None
depends_on = None


def upgrade():
    """Add performance indexes."""
    
    # Reviews table indexes for faster queries
    op.create_index('idx_reviews_app_id_platform', 'reviews', ['app_id', 'platform'])
    op.create_index('idx_reviews_website_url', 'reviews', ['website_url'])
    op.create_index('idx_reviews_rating', 'reviews', ['rating'])
    op.create_index('idx_reviews_date', 'reviews', ['review_date'])
    op.create_index('idx_reviews_platform', 'reviews', ['platform'])
    op.create_index('idx_reviews_processed', 'reviews', ['processed'])
    
    # Composite index for common query patterns
    op.create_index('idx_reviews_app_platform_rating', 'reviews', ['app_id', 'platform', 'rating'])
    op.create_index('idx_reviews_website_rating_date', 'reviews', ['website_url', 'rating', 'review_date'])
    
    # Analyses table indexes
    op.create_index('idx_analyses_app_id_platform', 'analyses', ['app_id', 'platform'])
    op.create_index('idx_analyses_website_url', 'analyses', ['website_url'])
    op.create_index('idx_analyses_status', 'analyses', ['status'])
    op.create_index('idx_analyses_created_at', 'analyses', ['created_at'])
    op.create_index('idx_analyses_completed_at', 'analyses', ['completed_at'])
    op.create_index('idx_analyses_task_id', 'analyses', ['task_id'])
    
    # Complaint clusters indexes
    op.create_index('idx_clusters_analysis_id', 'complaint_clusters', ['analysis_id'])
    op.create_index('idx_clusters_percentage', 'complaint_clusters', ['percentage'])
    op.create_index('idx_clusters_recency_score', 'complaint_clusters', ['recency_score'])
    
    # Composite index for ranking clusters
    op.create_index('idx_clusters_analysis_percentage_recency', 'complaint_clusters', 
                   ['analysis_id', 'percentage', 'recency_score'])


def downgrade():
    """Remove performance indexes."""
    
    # Reviews table indexes
    op.drop_index('idx_reviews_app_id_platform')
    op.drop_index('idx_reviews_website_url')
    op.drop_index('idx_reviews_rating')
    op.drop_index('idx_reviews_date')
    op.drop_index('idx_reviews_platform')
    op.drop_index('idx_reviews_processed')
    op.drop_index('idx_reviews_app_platform_rating')
    op.drop_index('idx_reviews_website_rating_date')
    
    # Analyses table indexes
    op.drop_index('idx_analyses_app_id_platform')
    op.drop_index('idx_analyses_website_url')
    op.drop_index('idx_analyses_status')
    op.drop_index('idx_analyses_created_at')
    op.drop_index('idx_analyses_completed_at')
    op.drop_index('idx_analyses_task_id')
    
    # Complaint clusters indexes
    op.drop_index('idx_clusters_analysis_id')
    op.drop_index('idx_clusters_percentage')
    op.drop_index('idx_clusters_recency_score')
    op.drop_index('idx_clusters_analysis_percentage_recency')