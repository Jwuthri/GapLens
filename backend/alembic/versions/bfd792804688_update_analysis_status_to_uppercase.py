"""update_analysis_status_to_uppercase

Revision ID: bfd792804688
Revises: add_metadata_to_reviews
Create Date: 2025-09-14 17:13:50.566748

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bfd792804688'
down_revision: Union[str, None] = 'add_metadata_to_reviews'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Update existing analysis status values from lowercase to uppercase
    op.execute("""
        UPDATE analyses 
        SET status = 'PENDING' 
        WHERE status = 'pending'
    """)
    
    op.execute("""
        UPDATE analyses 
        SET status = 'PROCESSING' 
        WHERE status = 'processing'
    """)
    
    op.execute("""
        UPDATE analyses 
        SET status = 'COMPLETED' 
        WHERE status = 'completed'
    """)
    
    op.execute("""
        UPDATE analyses 
        SET status = 'FAILED' 
        WHERE status = 'failed'
    """)


def downgrade() -> None:
    # Revert status values back to lowercase
    op.execute("""
        UPDATE analyses 
        SET status = 'pending' 
        WHERE status = 'PENDING'
    """)
    
    op.execute("""
        UPDATE analyses 
        SET status = 'processing' 
        WHERE status = 'PROCESSING'
    """)
    
    op.execute("""
        UPDATE analyses 
        SET status = 'completed' 
        WHERE status = 'COMPLETED'
    """)
    
    op.execute("""
        UPDATE analyses 
        SET status = 'failed' 
        WHERE status = 'FAILED'
    """)
