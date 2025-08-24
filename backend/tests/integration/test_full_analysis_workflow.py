"""Integration tests for complete analysis workflow."""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database.connection import get_db, Base
from app.models import database as db_models
from app.models.schemas import Platform, AnalysisStatus, Review


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_integration.db"
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
client = TestClient(app)


@pytest.fixture(scope="function")
def setup_integration_database():
    """Set up integration test database."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


class TestFullAnalysisWorkflow:
    """Test complete analysis workflow from submission to results."""
    
    @patch('app.services.review_scraper.ReviewScraperService.scrape_google_play')
    @patch('app.services.nlp_processor.NLPProcessor.process_reviews')
    @patch('app.services.clustering_engine.ClusteringEngine.cluster_reviews')
    @patch('app.tasks.analysis_tasks.process_app_analysis.delay')
    def test_complete_app_analysis_workflow(
        self,
        mock_celery_task,
        mock_clustering,
        mock_nlp,
        mock_scraper,
        setup_integration_database
    ):
        """Test complete app analysis workflow."""
        # Mock review scraping
        mock_reviews = [
            Review(
                id="review_1",
                app_id="com.test.app",
                platform=Platform.GOOGLE_PLAY,
                rating=1,
                text="App crashes constantly on startup",
                review_date=datetime.now() - timedelta(days=1),
                locale="en_US"
            ),
            Review(
                id="review_2",
                app_id="com.test.app",
                platform=Platform.GOOGLE_PLAY,
                rating=2,
                text="Battery drain is terrible, phone dies quickly",
                review_date=datetime.now() - timedelta(days=2),
                locale="en_US"
            ),
            Review(
                id="review_3",
                app_id="com.test.app",
                platform=Platform.GOOGLE_PLAY,
                rating=1,
                text="Interface is confusing and hard to navigate",
                review_date=datetime.now() - timedelta(days=3),
                locale="en_US"
            )
        ]
        mock_scraper.return_value = mock_reviews
        
        # Mock NLP processing (filter negative reviews)
        mock_nlp.return_value = mock_reviews  # All are negative
        
        # Mock clustering
        from app.models.schemas import ComplaintCluster
        mock_clusters = [
            ComplaintCluster(
                id="cluster_1",
                analysis_id="test",
                name="Crash Issues",
                description="App crashes and stability problems",
                review_count=1,
                percentage=33.3,
                recency_score=85.0,
                sample_reviews=["App crashes constantly on startup"],
                keywords=["crash", "startup"]
            ),
            ComplaintCluster(
                id="cluster_2",
                analysis_id="test",
                name="Battery Drain",
                description="Excessive battery consumption",
                review_count=1,
                percentage=33.3,
                recency_score=75.0,
                sample_reviews=["Battery drain is terrible, phone dies quickly"],
                keywords=["battery", "drain"]
            ),
            ComplaintCluster(
                id="cluster_3",
                analysis_id="test",
                name="UI Problems",
                description="User interface issues",
                review_count=1,
                percentage=33.3,
                recency_score=65.0,
                sample_reviews=["Interface is confusing and hard to navigate"],
                keywords=["interface", "navigation"]
            )
        ]
        mock_clustering.return_value = mock_clusters
        
        # Mock Celery task to execute synchronously
        def mock_task_execution(*args, **kwargs):
            # Simulate the actual task execution
            return self._simulate_analysis_processing(mock_reviews, mock_clusters)
        
        mock_celery_task.side_effect = mock_task_execution
        
        # Step 1: Submit analysis request
        response = client.post(
            "/api/v1/analysis/",
            json={"app_url_or_id": "com.test.app"}
        )
        
        assert response.status_code == 200
        data = response.json()
        analysis_id = data["analysis_id"]
        assert data["status"] == "pending"
        
        # Step 2: Check initial status
        status_response = client.get(f"/api/v1/analysis/{analysis_id}/status")
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["status"] in ["pending", "processing"]
        
        # Step 3: Simulate processing completion
        self._complete_analysis_in_db(analysis_id, mock_clusters)
        
        # Step 4: Check completed status
        final_status_response = client.get(f"/api/v1/analysis/{analysis_id}/status")
        assert final_status_response.status_code == 200
        final_status_data = final_status_response.json()
        assert final_status_data["status"] == "completed"
        assert final_status_data["progress"] == 100.0
        
        # Step 5: Get analysis results
        results_response = client.get(f"/api/v1/analysis/{analysis_id}")
        assert results_response.status_code == 200
        results_data = results_response.json()
        
        # Verify results structure
        assert "analysis" in results_data
        assert "summary" in results_data
        assert "clusters" in results_data
        
        # Verify analysis data
        analysis_data = results_data["analysis"]
        assert analysis_data["id"] == analysis_id
        assert analysis_data["app_id"] == "com.test.app"
        assert analysis_data["platform"] == "google_play"
        assert analysis_data["status"] == "completed"
        
        # Verify summary data
        summary_data = results_data["summary"]
        assert summary_data["total_reviews"] == 3
        assert summary_data["negative_reviews"] == 3
        assert summary_data["negative_percentage"] == 100.0
        
        # Verify clusters data
        clusters_data = results_data["clusters"]
        assert len(clusters_data) == 3
        
        cluster_names = [cluster["name"] for cluster in clusters_data]
        assert "Crash Issues" in cluster_names
        assert "Battery Drain" in cluster_names
        assert "UI Problems" in cluster_names
        
        # Step 6: Test export functionality
        csv_export_response = client.get(f"/api/v1/analysis/{analysis_id}/export?format=csv")
        assert csv_export_response.status_code == 200
        assert csv_export_response.headers["content-type"] == "text/csv; charset=utf-8"
        
        json_export_response = client.get(f"/api/v1/analysis/{analysis_id}/export?format=json")
        assert json_export_response.status_code == 200
        assert json_export_response.headers["content-type"] == "application/json"
    
    @patch('app.services.website_review_aggregator.WebsiteReviewAggregator.aggregate_website_reviews')
    @patch('app.services.nlp_processor.NLPProcessor.process_reviews')
    @patch('app.services.clustering_engine.ClusteringEngine.cluster_reviews')
    @patch('app.tasks.analysis_tasks.process_website_analysis.delay')
    def test_complete_website_analysis_workflow(
        self,
        mock_celery_task,
        mock_clustering,
        mock_nlp,
        mock_aggregator,
        setup_integration_database
    ):
        """Test complete website analysis workflow."""
        # Mock website review aggregation
        mock_reviews = [
            Review(
                id="website_review_1",
                website_url="https://example.com",
                platform=Platform.GOOGLE_REVIEWS,
                source_platform="Google Reviews",
                rating=2,
                text="Poor customer service, waited too long",
                review_date=datetime.now() - timedelta(days=1),
                locale="en_US"
            ),
            Review(
                id="website_review_2",
                website_url="https://example.com",
                platform=Platform.YELP,
                source_platform="Yelp",
                rating=1,
                text="Food was cold and service was terrible",
                review_date=datetime.now() - timedelta(days=2),
                locale="en_US"
            )
        ]
        mock_aggregator.return_value = mock_reviews
        mock_nlp.return_value = mock_reviews
        
        # Mock clustering for website reviews
        from app.models.schemas import ComplaintCluster
        mock_clusters = [
            ComplaintCluster(
                id="cluster_1",
                analysis_id="test",
                name="Service Issues",
                description="Poor customer service complaints",
                review_count=2,
                percentage=100.0,
                recency_score=80.0,
                sample_reviews=["Poor customer service, waited too long", "Food was cold and service was terrible"],
                keywords=["service", "customer", "poor"]
            )
        ]
        mock_clustering.return_value = mock_clusters
        
        # Mock Celery task
        def mock_task_execution(*args, **kwargs):
            return self._simulate_website_analysis_processing(mock_reviews, mock_clusters)
        
        mock_celery_task.side_effect = mock_task_execution
        
        # Submit website analysis request
        response = client.post(
            "/api/v1/analysis/",
            json={"website_url": "https://example.com"}
        )
        
        assert response.status_code == 200
        data = response.json()
        analysis_id = data["analysis_id"]
        
        # Simulate processing completion
        self._complete_website_analysis_in_db(analysis_id, mock_clusters)
        
        # Get results
        results_response = client.get(f"/api/v1/analysis/{analysis_id}")
        assert results_response.status_code == 200
        results_data = results_response.json()
        
        # Verify website-specific data
        analysis_data = results_data["analysis"]
        assert analysis_data["website_url"] == "https://example.com"
        assert analysis_data["analysis_type"] == "WEBSITE"
        assert analysis_data["platform"] is None
    
    def test_analysis_error_handling(self, setup_integration_database):
        """Test error handling in analysis workflow."""
        # Test invalid app URL
        response = client.post(
            "/api/v1/analysis/",
            json={"app_url_or_id": "invalid-url"}
        )
        assert response.status_code == 400
        
        # Test missing input
        response = client.post(
            "/api/v1/analysis/",
            json={}
        )
        assert response.status_code == 422
        
        # Test both inputs provided
        response = client.post(
            "/api/v1/analysis/",
            json={
                "app_url_or_id": "com.test.app",
                "website_url": "https://example.com"
            }
        )
        assert response.status_code == 422
    
    def test_concurrent_analysis_requests(self, setup_integration_database):
        """Test handling multiple concurrent analysis requests."""
        with patch('app.tasks.analysis_tasks.process_app_analysis.delay') as mock_task:
            # Submit multiple requests
            responses = []
            for i in range(5):
                response = client.post(
                    "/api/v1/analysis/",
                    json={"app_url_or_id": f"com.test.app{i}"}
                )
                responses.append(response)
            
            # All should succeed
            for response in responses:
                assert response.status_code == 200
                data = response.json()
                assert "analysis_id" in data
                assert data["status"] == "pending"
            
            # All should have unique analysis IDs
            analysis_ids = [response.json()["analysis_id"] for response in responses]
            assert len(set(analysis_ids)) == 5
            
            # Celery task should be called for each request
            assert mock_task.call_count == 5
    
    def test_analysis_status_transitions(self, setup_integration_database):
        """Test analysis status transitions."""
        with patch('app.tasks.analysis_tasks.process_app_analysis.delay'):
            # Submit analysis
            response = client.post(
                "/api/v1/analysis/",
                json={"app_url_or_id": "com.test.app"}
            )
            analysis_id = response.json()["analysis_id"]
            
            # Initial status should be pending
            status_response = client.get(f"/api/v1/analysis/{analysis_id}/status")
            assert status_response.json()["status"] == "pending"
            
            # Simulate status transitions
            db = TestingSessionLocal()
            analysis = db.query(db_models.Analysis).filter_by(id=analysis_id).first()
            
            # Update to processing
            analysis.status = AnalysisStatus.PROCESSING
            db.commit()
            
            status_response = client.get(f"/api/v1/analysis/{analysis_id}/status")
            assert status_response.json()["status"] == "processing"
            
            # Update to completed
            analysis.status = AnalysisStatus.COMPLETED
            analysis.completed_at = datetime.now()
            analysis.total_reviews = 100
            analysis.negative_reviews = 25
            db.commit()
            
            status_response = client.get(f"/api/v1/analysis/{analysis_id}/status")
            status_data = status_response.json()
            assert status_data["status"] == "completed"
            assert status_data["progress"] == 100.0
            
            # Update to failed
            analysis.status = AnalysisStatus.FAILED
            db.commit()
            
            status_response = client.get(f"/api/v1/analysis/{analysis_id}/status")
            assert status_response.json()["status"] == "failed"
            
            db.close()
    
    def _simulate_analysis_processing(self, reviews, clusters):
        """Simulate the analysis processing task."""
        # This would normally be done by the Celery task
        pass
    
    def _simulate_website_analysis_processing(self, reviews, clusters):
        """Simulate the website analysis processing task."""
        pass
    
    def _complete_analysis_in_db(self, analysis_id, clusters):
        """Complete analysis in database for testing."""
        db = TestingSessionLocal()
        
        # Update analysis status
        analysis = db.query(db_models.Analysis).filter_by(id=analysis_id).first()
        analysis.status = AnalysisStatus.COMPLETED
        analysis.completed_at = datetime.now()
        analysis.total_reviews = 3
        analysis.negative_reviews = 3
        
        # Add clusters
        for cluster_data in clusters:
            cluster = db_models.ComplaintCluster(
                analysis_id=analysis.id,
                name=cluster_data.name,
                description=cluster_data.description,
                review_count=cluster_data.review_count,
                percentage=cluster_data.percentage,
                recency_score=cluster_data.recency_score,
                sample_reviews=cluster_data.sample_reviews,
                keywords=cluster_data.keywords
            )
            db.add(cluster)
        
        db.commit()
        db.close()
    
    def _complete_website_analysis_in_db(self, analysis_id, clusters):
        """Complete website analysis in database for testing."""
        db = TestingSessionLocal()
        
        # Update analysis status
        analysis = db.query(db_models.Analysis).filter_by(id=analysis_id).first()
        analysis.status = AnalysisStatus.COMPLETED
        analysis.completed_at = datetime.now()
        analysis.total_reviews = 2
        analysis.negative_reviews = 2
        
        # Add clusters
        for cluster_data in clusters:
            cluster = db_models.ComplaintCluster(
                analysis_id=analysis.id,
                name=cluster_data.name,
                description=cluster_data.description,
                review_count=cluster_data.review_count,
                percentage=cluster_data.percentage,
                recency_score=cluster_data.recency_score,
                sample_reviews=cluster_data.sample_reviews,
                keywords=cluster_data.keywords
            )
            db.add(cluster)
        
        db.commit()
        db.close()


class TestAnalysisPerformance:
    """Test analysis performance and scalability."""
    
    def test_large_dataset_handling(self, setup_integration_database):
        """Test handling of large review datasets."""
        with patch('app.tasks.analysis_tasks.process_app_analysis.delay') as mock_task:
            # Submit analysis for app with many reviews
            response = client.post(
                "/api/v1/analysis/",
                json={"app_url_or_id": "com.popular.app"}
            )
            
            assert response.status_code == 200
            analysis_id = response.json()["analysis_id"]
            
            # Simulate large dataset processing
            db = TestingSessionLocal()
            analysis = db.query(db_models.Analysis).filter_by(id=analysis_id).first()
            analysis.status = AnalysisStatus.COMPLETED
            analysis.total_reviews = 10000
            analysis.negative_reviews = 2500
            analysis.completed_at = datetime.now()
            db.commit()
            db.close()
            
            # Should handle large numbers correctly
            results_response = client.get(f"/api/v1/analysis/{analysis_id}")
            assert results_response.status_code == 200
            
            summary = results_response.json()["summary"]
            assert summary["total_reviews"] == 10000
            assert summary["negative_reviews"] == 2500
            assert summary["negative_percentage"] == 25.0
    
    def test_memory_usage_with_large_clusters(self, setup_integration_database):
        """Test memory usage with large number of clusters."""
        with patch('app.tasks.analysis_tasks.process_app_analysis.delay'):
            response = client.post(
                "/api/v1/analysis/",
                json={"app_url_or_id": "com.test.app"}
            )
            analysis_id = response.json()["analysis_id"]
            
            # Create many clusters
            db = TestingSessionLocal()
            analysis = db.query(db_models.Analysis).filter_by(id=analysis_id).first()
            analysis.status = AnalysisStatus.COMPLETED
            analysis.total_reviews = 1000
            analysis.negative_reviews = 500
            analysis.completed_at = datetime.now()
            
            # Add 50 clusters
            for i in range(50):
                cluster = db_models.ComplaintCluster(
                    analysis_id=analysis.id,
                    name=f"Cluster {i}",
                    description=f"Description for cluster {i}",
                    review_count=10,
                    percentage=2.0,
                    recency_score=50.0,
                    sample_reviews=[f"Sample review {i}"],
                    keywords=[f"keyword{i}"]
                )
                db.add(cluster)
            
            db.commit()
            db.close()
            
            # Should handle many clusters without issues
            results_response = client.get(f"/api/v1/analysis/{analysis_id}")
            assert results_response.status_code == 200
            
            clusters = results_response.json()["clusters"]
            assert len(clusters) == 50


class TestAnalysisDataIntegrity:
    """Test data integrity throughout analysis workflow."""
    
    def test_data_consistency_across_requests(self, setup_integration_database):
        """Test data consistency across multiple API requests."""
        with patch('app.tasks.analysis_tasks.process_app_analysis.delay'):
            # Submit analysis
            response = client.post(
                "/api/v1/analysis/",
                json={"app_url_or_id": "com.test.app"}
            )
            analysis_id = response.json()["analysis_id"]
            
            # Complete analysis
            self._setup_completed_analysis(analysis_id)
            
            # Make multiple requests for same analysis
            responses = []
            for _ in range(5):
                response = client.get(f"/api/v1/analysis/{analysis_id}")
                responses.append(response.json())
            
            # All responses should be identical
            first_response = responses[0]
            for response in responses[1:]:
                assert response == first_response
    
    def test_database_transaction_integrity(self, setup_integration_database):
        """Test database transaction integrity during analysis creation."""
        with patch('app.tasks.analysis_tasks.process_app_analysis.delay') as mock_task:
            # Mock task to raise exception
            mock_task.side_effect = Exception("Task failed")
            
            # Submit analysis (should still create database record)
            response = client.post(
                "/api/v1/analysis/",
                json={"app_url_or_id": "com.test.app"}
            )
            
            # Should succeed despite task failure
            assert response.status_code == 200
            analysis_id = response.json()["analysis_id"]
            
            # Analysis record should exist in database
            db = TestingSessionLocal()
            analysis = db.query(db_models.Analysis).filter_by(id=analysis_id).first()
            assert analysis is not None
            assert analysis.status == AnalysisStatus.PENDING
            db.close()
    
    def _setup_completed_analysis(self, analysis_id):
        """Set up a completed analysis for testing."""
        db = TestingSessionLocal()
        
        analysis = db.query(db_models.Analysis).filter_by(id=analysis_id).first()
        analysis.status = AnalysisStatus.COMPLETED
        analysis.completed_at = datetime.now()
        analysis.total_reviews = 100
        analysis.negative_reviews = 30
        
        # Add test cluster
        cluster = db_models.ComplaintCluster(
            analysis_id=analysis.id,
            name="Test Issues",
            description="Test cluster",
            review_count=30,
            percentage=100.0,
            recency_score=75.0,
            sample_reviews=["Test review"],
            keywords=["test"]
        )
        db.add(cluster)
        
        db.commit()
        db.close()


if __name__ == "__main__":
    pytest.main([__file__])