"""Database connection and session management utilities with connection pooling."""

import os
import logging
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy.engine import Engine

# Database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/review_gap_analyzer")

# Connection pool configuration
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))  # 1 hour

logger = logging.getLogger(__name__)

# Create SQLAlchemy engine with optimized connection pooling
engine = create_engine(
    DATABASE_URL,
    # Connection pooling settings
    poolclass=QueuePool,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_recycle=POOL_RECYCLE,
    pool_pre_ping=True,
    
    # Performance settings
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
    echo_pool=os.getenv("SQL_ECHO_POOL", "false").lower() == "true",
    
    # Connection settings
    connect_args={
        "connect_timeout": 10,
        "application_name": "review_gap_analyzer",
        # PostgreSQL-specific optimizations
        "options": "-c default_transaction_isolation='read committed'"
    }
)

# Add connection event listeners for monitoring
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set connection-level optimizations."""
    if "postgresql" in DATABASE_URL:
        # PostgreSQL optimizations
        with dbapi_connection.cursor() as cursor:
            # Set connection-level settings for better performance
            cursor.execute("SET synchronous_commit = off")  # Faster writes, slight durability trade-off
            cursor.execute("SET wal_buffers = '16MB'")
            cursor.execute("SET checkpoint_completion_target = 0.9")

@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Log connection checkout for monitoring."""
    logger.debug("Connection checked out from pool")

@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    """Log connection checkin for monitoring."""
    logger.debug("Connection returned to pool")

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """Drop all tables in the database (for testing)."""
    Base.metadata.drop_all(bind=engine)