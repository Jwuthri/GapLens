"""Tests for analysis API endpoints."""

import json
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database.connection import get_db, Base
from app.models import database as db_models
from app.models.schemas import Platform, AnalysisStatus


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

# Create test client
client = TestClient(app)


@pytest.fixture(scope="function")
def setup_database():
    """Set up test database."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


class TestAnalysisEndpoints:
    """Test class for analysis API endpoints."""
    
    def test_submit_app_analysis_valid_url(self, setup_database):
        """Test submitting analysis with valid Google Play URL."""
        with patch('app.api.v1.analysis.process_app_analysis') as mock_process:
            response = client.post(
                "/api/v1/analysis/",
                json={
                    "app_url_or_id": "https://play.google.com/store/apps/details?id=com.example.app"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "analysis_id" in data
            assert data["status"] == "pending"
            assert "message" in data
            mock_process.assert_called_once()
    
    def test_submit_app_analysis_valid_app_id(self, setup_database):
        """Test submitting analysis with valid app ID."""
        with patch('app.api.v1.analysis.process_app_analysis') as mock_process:
            response = client.post(
                "/api/v1/analysis/",
                json={
                    "app_url_or_id": "com.example.app"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "analysis_id" in data
            assert data["status"] == "pending"
            mock_process.assert_called_once()
    
    def test_submit_website_analysis_valid_url(self, setup_database):
        """Test submitting analysis with valid website URL."""
        with patch('app.api.v1.analysis.process_website_analysis') as mock_process:
            response = client.post(
                "/api/v1/analysis/",
                json={
                    "website_url": "https://example.com"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "analysis_id" in data
            assert data["status"] == "pending"
            mock_process.assert_called_once()
    
    def test_submit_analysis_invalid_app_url(self, setup_database):
        """Test submitting analysis with invalid app URL."""
        response = client.post(
            "/api/v1/analysis/",
            json={
                "app_url_or_id": "invalid-url"
            }
        )
        
        assert response.status_code == 400
        assert "Invalid app URL or ID" in response.json()["detail"]
    
    def test_submit_analysis_no_input(self, setup_database):
        """Test submitting analysis with no input."""
        response = client.post(
            "/api/v1/analysis/",
            json={}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_submit_analysis_both_inputs(self, setup_database):
        """Test submitting analysis with both app and website inputs."""
        response = client.post(
            "/api/v1/analysis/",
            json={
                "app_url_or_id": "com.example.app",
                "website_url": "https://example.com"
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_get_analysis_results_completed(self, setup_database):
        """Test getting results for completed analysis."""
        # Create test analysis with clusters
        db = TestingSessionLocal()
        
        analysis = db_models.Analysis(
            id=uuid4(),
            app_id="com.example.app",
            analysis_type="APP",
            platform=Platform.GOOGLE_PLAY,
            status=AnalysisStatus.COMPLETED,
            total_reviews=100,
            negative_reviews=25,
            completed_at=datetime.now()
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        
        # Add test cluster
        cluster = db_models.ComplaintCluster(
            analysis_id=analysis.id,
            name="Test Issues",
            description="Test cluster description",
            review_count=10,
            percentage=40.0,
            recency_score=75.0,
            sample_reviews=["Test review 1", "Test review 2"],
            keywords=["test", "issue"]
        )
        db.add(cluster)
        db.commit()
        
        response = client.get(f"/api/v1/analysis/{analysis.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["analysis"]["id"] == str(analysis.id)
        assert data["summary"]["total_reviews"] == 100
        assert len(data["clusters"]) == 1
        assert data["clusters"][0]["name"] == "Test Issues"
        
        db.close()
    
    def test_get_analysis_results_not_found(self, setup_database):
        """Test getting results for non-existent analysis."""
        fake_id = uuid4()
        response = client.get(f"/api/v1/analysis/{fake_id}")
        
        assert response.status_code == 404
        assert "Analysis not found" in response.json()["detail"]
    
    def test_get_analysis_results_not_completed(self, setup_database):
        """Test getting results for incomplete analysis."""
        db = TestingSessionLocal()
        
        analysis = db_models.Analysis(
            id=uuid4(),
            app_id="com.example.app",
            analysis_type="APP",
            platform=Platform.GOOGLE_PLAY,
            status=AnalysisStatus.PROCESSING
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        
        response = client.get(f"/api/v1/analysis/{analysis.id}")
        
        assert response.status_code == 400
        assert "not completed" in response.json()["detail"]
        
        db.close()
    
    def test_get_analysis_status_pending(self, setup_database):
        """Test getting status for pending analysis."""
        db = TestingSessionLocal()
        
        analysis = db_models.Analysis(
            id=uuid4(),
            app_id="com.example.app",
            analysis_type="APP",
            platform=Platform.GOOGLE_PLAY,
            status=AnalysisStatus.PENDING
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        
        response = client.get(f"/api/v1/analysis/{analysis.id}/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["analysis_id"] == str(analysis.id)
        assert data["status"] == "pending"
        assert data["progress"] == 0.0
        assert "queued" in data["message"]
        
        db.close()
    
    def test_get_analysis_status_processing(self, setup_database):
        """Test getting status for processing analysis."""
        db = TestingSessionLocal()
        
        analysis = db_models.Analysis(
            id=uuid4(),
            app_id="com.example.app",
            analysis_type="APP",
            platform=Platform.GOOGLE_PLAY,
            status=AnalysisStatus.PROCESSING
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        
        response = client.get(f"/api/v1/analysis/{analysis.id}/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert data["progress"] == 50.0
        
        db.close()
    
    def test_get_analysis_status_completed(self, setup_database):
        """Test getting status for completed analysis."""
        db = TestingSessionLocal()
        
        analysis = db_models.Analysis(
            id=uuid4(),
            app_id="com.example.app",
            analysis_type="APP",
            platform=Platform.GOOGLE_PLAY,
            status=AnalysisStatus.COMPLETED,
            completed_at=datetime.now()
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        
        response = client.get(f"/api/v1/analysis/{analysis.id}/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["progress"] == 100.0
        
        db.close()
    
    def test_get_analysis_status_not_found(self, setup_database):
        """Test getting status for non-existent analysis."""
        fake_id = uuid4()
        response = client.get(f"/api/v1/analysis/{fake_id}/status")
        
        assert response.status_code == 404
        assert "Analysis not found" in response.json()["detail"]
    
    def test_export_analysis_json(self, setup_database):
        """Test exporting analysis results as JSON."""
        db = TestingSessionLocal()
        
        analysis = db_models.Analysis(
            id=uuid4(),
            app_id="com.example.app",
            analysis_type="APP",
            platform=Platform.GOOGLE_PLAY,
            status=AnalysisStatus.COMPLETED,
            total_reviews=100,
            negative_reviews=25,
            completed_at=datetime.now()
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        
        # Add test cluster
        cluster = db_models.ComplaintCluster(
            analysis_id=analysis.id,
            name="Test Issues",
            description="Test cluster description",
            review_count=10,
            percentage=40.0,
            recency_score=75.0,
            sample_reviews=["Test review 1"],
            keywords=["test"]
        )
        db.add(cluster)
        db.commit()
        
        response = client.get(f"/api/v1/analysis/{analysis.id}/export?format=json")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert "attachment" in response.headers["content-disposition"]
        
        # Verify JSON content
        data = json.loads(response.content)
        assert data["analysis_id"] == str(analysis.id)
        assert data["total_reviews"] == 100
        assert len(data["clusters"]) == 1
        
        db.close()
    
    def test_export_analysis_csv(self, setup_database):
        """Test exporting analysis results as CSV."""
        db = TestingSessionLocal()
        
        analysis = db_models.Analysis(
            id=uuid4(),
            app_id="com.example.app",
            analysis_type="APP",
            platform=Platform.GOOGLE_PLAY,
            status=AnalysisStatus.COMPLETED,
            total_reviews=100,
            negative_reviews=25,
            completed_at=datetime.now()
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        
        # Add test cluster
        cluster = db_models.ComplaintCluster(
            analysis_id=analysis.id,
            name="Test Issues",
            description="Test cluster description",
            review_count=10,
            percentage=40.0,
            recency_score=75.0,
            sample_reviews=["Test review 1"],
            keywords=["test"]
        )
        db.add(cluster)
        db.commit()
        
        response = client.get(f"/api/v1/analysis/{analysis.id}/export?format=csv")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]
        
        # Verify CSV content contains headers
        content = response.content.decode('utf-8')
        assert "Analysis ID" in content
        assert "Cluster Name" in content
        assert str(analysis.id) in content
        
        db.close()
    
    def test_export_analysis_not_found(self, setup_database):
        """Test exporting non-existent analysis."""
        fake_id = uuid4()
        response = client.get(f"/api/v1/analysis/{fake_id}/export")
        
        assert response.status_code == 404
        assert "Analysis not found" in response.json()["detail"]
    
    def test_export_analysis_not_completed(self, setup_database):
        """Test exporting incomplete analysis."""
        db = TestingSessionLocal()
        
        analysis = db_models.Analysis(
            id=uuid4(),
            app_id="com.example.app",
            analysis_type="APP",
            platform=Platform.GOOGLE_PLAY,
            status=AnalysisStatus.PROCESSING
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        
        response = client.get(f"/api/v1/analysis/{analysis.id}/export")
        
        assert response.status_code == 400
        assert "not completed" in response.json()["detail"]
        
        db.close()


if __name__ == "__main__":
    pytest.main([__file__])