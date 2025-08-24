"""Tests for database connection utilities."""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database.connection import Base, SessionLocal, create_tables, drop_tables, get_db


class TestDatabaseConnection:
    """Tests for database connection utilities."""
    
    def test_get_db_generator(self):
        """Test that get_db returns a generator."""
        db_gen = get_db()
        assert hasattr(db_gen, '__next__')  # Check if it's a generator
    
    def test_get_db_session_cleanup(self):
        """Test that get_db properly cleans up sessions."""
        # This test ensures the session is properly closed
        db_gen = get_db()
        session = next(db_gen)
        
        # Session should be valid
        assert session is not None
        assert hasattr(session, 'query')
        
        # Cleanup should work without errors
        try:
            next(db_gen)
        except StopIteration:
            pass  # Expected behavior
    
    def test_create_and_drop_tables(self):
        """Test table creation and dropping."""
        # Use in-memory SQLite for testing
        test_engine = create_engine("sqlite:///:memory:")
        
        # Test table creation
        Base.metadata.create_all(bind=test_engine)
        
        # Verify tables exist
        with test_engine.connect() as conn:
            # Check if tables exist by querying sqlite_master
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            table_names = [row[0] for row in result]
            
            expected_tables = ['reviews', 'analyses', 'complaint_clusters']
            for table in expected_tables:
                assert table in table_names
        
        # Test table dropping
        Base.metadata.drop_all(bind=test_engine)
        
        # Verify tables are dropped
        with test_engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            table_names = [row[0] for row in result]
            
            expected_tables = ['reviews', 'analyses', 'complaint_clusters']
            for table in expected_tables:
                assert table not in table_names
    
    def test_session_local_configuration(self):
        """Test SessionLocal configuration."""
        session = SessionLocal()
        
        try:
            # Test basic session properties
            assert session is not None
            assert hasattr(session, 'query')
            assert hasattr(session, 'add')
            assert hasattr(session, 'commit')
            assert hasattr(session, 'rollback')
            
            # Test autoflush settings (autocommit is deprecated in SQLAlchemy 2.0)
            assert session.autoflush is False
            
        finally:
            session.close()


class TestDatabaseIntegration:
    """Integration tests for database operations."""
    
    def test_session_transaction_rollback(self, test_session):
        """Test that session rollback works properly."""
        from app.models.database import Review, Platform
        from datetime import datetime
        
        # Add a review
        review = Review(
            id="test_rollback",
            app_id="com.test.rollback",
            platform=Platform.GOOGLE_PLAY,
            rating=1,
            text="Test review for rollback",
            review_date=datetime.now()
        )
        
        test_session.add(review)
        
        # Flush to make it visible in the session (but not committed)
        test_session.flush()
        
        # Verify it's in the session but not committed
        assert test_session.query(Review).filter(Review.id == "test_rollback").first() is not None
        
        # Rollback the transaction
        test_session.rollback()
        
        # Verify the review is no longer in the session
        assert test_session.query(Review).filter(Review.id == "test_rollback").first() is None
    
    def test_session_transaction_commit(self, test_session):
        """Test that session commit works properly."""
        from app.models.database import Analysis, Platform, AnalysisStatus
        
        # Add an analysis
        analysis = Analysis(
            app_id="com.test.commit",
            analysis_type="APP",
            platform=Platform.GOOGLE_PLAY,
            status=AnalysisStatus.PENDING
        )
        
        test_session.add(analysis)
        test_session.commit()
        
        # Verify it's committed and can be queried
        saved_analysis = test_session.query(Analysis).filter(Analysis.app_id == "com.test.commit").first()
        assert saved_analysis is not None
        assert saved_analysis.app_id == "com.test.commit"
        assert saved_analysis.platform == Platform.GOOGLE_PLAY
        assert saved_analysis.status == AnalysisStatus.PENDING