"""Test configuration and fixtures."""

import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.connection import Base
from app.models.database import Analysis, ComplaintCluster, Review


# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="function")
def test_engine():
    """Create a test database engine."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_session(test_engine):
    """Create a test database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_review_data():
    """Sample review data for testing."""
    return {
        "id": "test_review_1",
        "app_id": "com.example.app",
        "platform": "google_play",
        "rating": 1,
        "text": "App crashes constantly, very frustrating experience",
        "review_date": "2024-01-15T10:30:00",
        "locale": "en_US"
    }


@pytest.fixture
def sample_analysis_data():
    """Sample analysis data for testing."""
    return {
        "app_id": "com.example.app",
        "platform": "google_play",
        "status": "pending"
    }


@pytest.fixture
def sample_cluster_data():
    """Sample complaint cluster data for testing."""
    return {
        "name": "Crash Issues",
        "description": "App crashes and stability problems",
        "review_count": 25,
        "percentage": 15.5,
        "recency_score": 85.2,
        "sample_reviews": ["App crashes on startup", "Constant crashes"],
        "keywords": ["crash", "stability", "bug"]
    }