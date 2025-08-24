"""End-to-end tests for complete user scenarios."""

import pytest
import time
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database.connection import get_db, Base
from app.models import database as db_models
from app.models.schemas import Platform, AnalysisStatus, Review, ComplaintCluster


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_e2e.db"
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
def setup_e2e_database():
    """Set up end-to-end test database."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


class TestEndToEndUserScenarios:
    """Test complete user scenarios from start to finish."""
    
    @patch('app.services.review_scraper.ReviewScraperService.scrape_google_play')
    @patch('app.services.nlp_processor.NLPProcessor.process_reviews')
    @patch('app.services.clustering_engine.ClusteringEngine.cluster_reviews')
    def test_developer_analyzes_app_reviews_scenario(
        self,
        mock_clustering,
        mock_nlp,
        mock_scraper,
        setup_e2e_database
    ):
        """
        Scenario: A developer wants to analyze their app's negative reviews
        to identify the most common user complaints and prioritize fixes.
        """
        # Setup: Mock realistic review data
        mock_reviews = self._create_realistic_review_dataset()
        mock_scraper.return_value = mock_reviews
        mock_nlp.return_value = [r for r in mock_reviews if r.rating <= 2]  # Filter negative
        
        # Mock realistic clustering results
        mock_clusters = self._create_realistic_clusters()
        mock_clustering.return_value = mock_clusters
        
        # Step 1: Developer submits their app for analysis
        print("Step 1: Submitting app for analysis...")
        submit_response = client.post(
            "/api/v1/analysis/",
            json={"app_url_or_id": "https://play.google.com/store/apps/details?id=com.mycompany.myapp"}
        )
        
        assert submit_response.status_code == 200
        submit_data = submit_response.json()
        analysis_id = submit_data["analysis_id"]
        
        print(f"Analysis submitted with ID: {analysis_id}")
        assert submit_data["status"] == "pending"
        assert "message" in submit_data
        
        # Step 2: Developer checks analysis status (polling simulation)
        print("Step 2: Checking analysis status...")
        
        # Simulate initial pending status
        status_response = client.get(f"/api/v1/analysis/{analysis_id}/status")
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["status"] == "pending"
        assert status_data["progress"] == 0.0
        
        # Simulate processing status
        self._update_analysis_status(analysis_id, AnalysisStatus.PROCESSING)
        
        status_response = client.get(f"/api/v1/analysis/{analysis_id}/status")
        status_data = status_response.json()
        assert status_data["status"] == "processing"
        assert status_data["progress"] == 50.0
        
        # Step 3: Analysis completes
        print("Step 3: Analysis completing...")
        self._complete_analysis_with_results(analysis_id, mock_reviews, mock_clusters)
        
        status_response = client.get(f"/api/v1/analysis/{analysis_id}/status")
        status_data = status_response.json()
        assert status_data["status"] == "completed"
        assert status_data["progress"] == 100.0
        
        # Step 4: Developer retrieves analysis results
        print("Step 4: Retrieving analysis results...")
        results_response = client.get(f"/api/v1/analysis/{analysis_id}")
        
        assert results_response.status_code == 200
        results_data = results_response.json()
        
        # Verify comprehensive results structure
        assert "analysis" in results_data
        assert "summary" in results_data
        assert "clusters" in results_data
        
        # Verify analysis metadata
        analysis_info = results_data["analysis"]
        assert analysis_info["app_id"] == "com.mycompany.myapp"
        assert analysis_info["platform"] == "google_play"
        assert analysis_info["status"] == "completed"
        
        # Verify summary statistics
        summary = results_data["summary"]
        assert summary["total_reviews"] > 0
        assert summary["negative_reviews"] > 0
        assert 0 <= summary["negative_percentage"] <= 100
        
        # Verify clusters are ranked by importance
        clusters = results_data["clusters"]
        assert len(clusters) >= 3
        
        # Clusters should be sorted by percentage (descending)
        for i in range(len(clusters) - 1):
            assert clusters[i]["percentage"] >= clusters[i + 1]["percentage"]
        
        # Verify each cluster has required information
        for cluster in clusters:
            assert "name" in cluster
            assert "description" in cluster
            assert "review_count" in cluster
            assert "percentage" in cluster
            assert "recency_score" in cluster
            assert "sample_reviews" in cluster
            assert "keywords" in cluster
            assert len(cluster["sample_reviews"]) > 0
        
        print(f"Found {len(clusters)} complaint clusters:")
        for i, cluster in enumerate(clusters, 1):
            print(f"  {i}. {cluster['name']}: {cluster['percentage']:.1f}% ({cluster['review_count']} reviews)")
        
        # Step 5: Developer exports results for team sharing
        print("Step 5: Exporting results...")
        
        # Export as CSV
        csv_response = client.get(f"/api/v1/analysis/{analysis_id}/export?format=csv")
        assert csv_response.status_code == 200
        assert csv_response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in csv_response.headers["content-disposition"]
        
        csv_content = csv_response.content.decode('utf-8')
        assert "Cluster Name" in csv_content
        assert "Percentage" in csv_content
        assert "Sample Reviews" in csv_content
        
        # Export as JSON
        json_response = client.get(f"/api/v1/analysis/{analysis_id}/export?format=json")
        assert json_response.status_code == 200
        assert json_response.headers["content-type"] == "application/json"
        
        json_content = json.loads(json_response.content)
        assert "analysis_id" in json_content
        assert "clusters" in json_content
        assert len(json_content["clusters"]) == len(clusters)
        
        print("Scenario completed successfully!")
    
    @patch('app.services.website_review_aggregator.WebsiteReviewAggregator.aggregate_website_reviews')
    @patch('app.services.nlp_processor.NLPProcessor.process_reviews')
    @patch('app.services.clustering_engine.ClusteringEngine.cluster_reviews')
    def test_business_owner_analyzes_website_reviews_scenario(
        self,
        mock_clustering,
        mock_nlp,
        mock_aggregator,
        setup_e2e_database
    ):
        """
        Scenario: A business owner wants to analyze online reviews across
        multiple platforms to understand customer complaints.
        """
        # Setup: Mock website review data from multiple sources
        mock_reviews = self._create_website_review_dataset()
        mock_aggregator.return_value = mock_reviews
        mock_nlp.return_value = [r for r in mock_reviews if r.rating and r.rating <= 2]
        
        # Mock website-specific clusters
        mock_clusters = self._create_website_clusters()
        mock_clustering.return_value = mock_clusters
        
        # Step 1: Business owner submits website for analysis
        print("Step 1: Submitting website for analysis...")
        submit_response = client.post(
            "/api/v1/analysis/",
            json={"website_url": "https://myrestaurant.com"}
        )
        
        assert submit_response.status_code == 200
        analysis_id = submit_response.json()["analysis_id"]
        
        # Step 2: Complete analysis
        print("Step 2: Processing website reviews from multiple platforms...")
        self._complete_website_analysis_with_results(analysis_id, mock_reviews, mock_clusters)
        
        # Step 3: Retrieve results
        print("Step 3: Retrieving website analysis results...")
        results_response = client.get(f"/api/v1/analysis/{analysis_id}")
        
        assert results_response.status_code == 200
        results_data = results_response.json()
        
        # Verify website-specific data
        analysis_info = results_data["analysis"]
        assert analysis_info["website_url"] == "https://myrestaurant.com"
        assert analysis_info["analysis_type"] == "WEBSITE"
        assert analysis_info["platform"] is None
        
        # Verify cross-platform insights
        clusters = results_data["clusters"]
        service_cluster = next((c for c in clusters if "service" in c["name"].lower()), None)
        assert service_cluster is not None
        
        print(f"Website analysis found {len(clusters)} complaint categories:")
        for cluster in clusters:
            print(f"  - {cluster['name']}: {cluster['percentage']:.1f}%")
        
        print("Website analysis scenario completed successfully!")
    
    def test_error_recovery_scenario(self, setup_e2e_database):
        """
        Scenario: User encounters various errors and the system handles them gracefully.
        """
        print("Testing error recovery scenarios...")
        
        # Scenario 1: Invalid app URL
        print("1. Testing invalid app URL...")
        response = client.post(
            "/api/v1/analysis/",
            json={"app_url_or_id": "https://invalid-store.com/app/123"}
        )
        assert response.status_code == 400
        error_data = response.json()
        assert "detail" in error_data
        assert "invalid" in error_data["detail"].lower()
        
        # Scenario 2: Malformed request
        print("2. Testing malformed request...")
        response = client.post(
            "/api/v1/analysis/",
            json={"invalid_field": "value"}
        )
        assert response.status_code == 422
        
        # Scenario 3: Both app and website provided
        print("3. Testing conflicting inputs...")
        response = client.post(
            "/api/v1/analysis/",
            json={
                "app_url_or_id": "com.test.app",
                "website_url": "https://example.com"
            }
        )
        assert response.status_code == 422
        
        # Scenario 4: Non-existent analysis ID
        print("4. Testing non-existent analysis...")
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/v1/analysis/{fake_id}")
        assert response.status_code == 404
        
        response = client.get(f"/api/v1/analysis/{fake_id}/status")
        assert response.status_code == 404
        
        response = client.get(f"/api/v1/analysis/{fake_id}/export")
        assert response.status_code == 404
        
        print("Error recovery scenarios completed successfully!")
    
    def test_concurrent_users_scenario(self, setup_e2e_database):
        """
        Scenario: Multiple users submit analyses simultaneously.
        """
        print("Testing concurrent users scenario...")
        
        with patch('app.tasks.analysis_tasks.process_app_analysis.delay') as mock_task:
            # Simulate 10 concurrent users
            responses = []
            for i in range(10):
                response = client.post(
                    "/api/v1/analysis/",
                    json={"app_url_or_id": f"com.test.app{i}"}
                )
                responses.append(response)
            
            # All requests should succeed
            analysis_ids = []
            for i, response in enumerate(responses):
                assert response.status_code == 200, f"Request {i} failed"
                data = response.json()
                analysis_ids.append(data["analysis_id"])
            
            # All analysis IDs should be unique
            assert len(set(analysis_ids)) == 10
            
            # Each analysis should be trackable
            for analysis_id in analysis_ids:
                status_response = client.get(f"/api/v1/analysis/{analysis_id}/status")
                assert status_response.status_code == 200
                assert status_response.json()["status"] == "pending"
        
        print("Concurrent users scenario completed successfully!")
    
    def test_large_app_analysis_scenario(self, setup_e2e_database):
        """
        Scenario: Analyzing a popular app with thousands of reviews.
        """
        print("Testing large app analysis scenario...")
        
        with patch('app.tasks.analysis_tasks.process_app_analysis.delay'):
            # Submit analysis for popular app
            response = client.post(
                "/api/v1/analysis/",
                json={"app_url_or_id": "com.popular.app"}
            )
            
            analysis_id = response.json()["analysis_id"]
            
            # Simulate large dataset processing
            large_dataset = self._create_large_review_dataset(5000)  # 5000 reviews
            large_clusters = self._create_many_clusters(20)  # 20 clusters
            
            self._complete_analysis_with_results(analysis_id, large_dataset, large_clusters)
            
            # Verify system handles large dataset
            results_response = client.get(f"/api/v1/analysis/{analysis_id}")
            assert results_response.status_code == 200
            
            results_data = results_response.json()
            summary = results_data["summary"]
            assert summary["total_reviews"] == 5000
            
            clusters = results_data["clusters"]
            assert len(clusters) == 20
            
            # Export should work with large dataset
            csv_response = client.get(f"/api/v1/analysis/{analysis_id}/export?format=csv")
            assert csv_response.status_code == 200
            
            print(f"Successfully processed {summary['total_reviews']} reviews into {len(clusters)} clusters")
        
        print("Large app analysis scenario completed successfully!")
    
    def _create_realistic_review_dataset(self):
        """Create a realistic dataset of app reviews."""
        reviews = []
        
        # Crash-related reviews
        crash_reviews = [
            "App crashes constantly when I try to open it",
            "Keeps crashing on my Android 14 device",
            "Crashes every time I try to save my work",
            "Unstable app, crashes multiple times per day",
            "App freezes and crashes during video calls"
        ]
        
        # Battery drain reviews
        battery_reviews = [
            "This app drains my battery way too fast",
            "Phone dies in 2 hours when using this app",
            "Terrible battery optimization, needs fixing",
            "Battery usage is through the roof with this app"
        ]
        
        # UI/UX reviews
        ui_reviews = [
            "Interface is confusing and hard to navigate",
            "Poor design choices make the app unusable",
            "UI is outdated and not user-friendly",
            "Can't find basic features, terrible UX"
        ]
        
        # Performance reviews
        performance_reviews = [
            "App is extremely slow and laggy",
            "Takes forever to load anything",
            "Performance has gotten worse with recent updates"
        ]
        
        # Positive reviews (should be filtered out)
        positive_reviews = [
            "Great app, love using it daily!",
            "Excellent features and smooth performance",
            "Best app in its category, highly recommend"
        ]
        
        all_review_texts = [
            (crash_reviews, 1),
            (battery_reviews, 2),
            (ui_reviews, 1),
            (performance_reviews, 2),
            (positive_reviews, 5)
        ]
        
        review_id = 1
        for review_list, rating in all_review_texts:
            for text in review_list:
                reviews.append(Review(
                    id=f"review_{review_id}",
                    app_id="com.mycompany.myapp",
                    platform=Platform.GOOGLE_PLAY,
                    rating=rating,
                    text=text,
                    review_date=datetime.now() - timedelta(days=review_id % 30),
                    locale="en_US"
                ))
                review_id += 1
        
        return reviews
    
    def _create_realistic_clusters(self):
        """Create realistic complaint clusters."""
        return [
            ComplaintCluster(
                id="cluster_1",
                analysis_id="test",
                name="App Crashes",
                description="Frequent app crashes and stability issues",
                review_count=5,
                percentage=35.7,
                recency_score=85.0,
                sample_reviews=[
                    "App crashes constantly when I try to open it",
                    "Keeps crashing on my Android 14 device",
                    "Crashes every time I try to save my work"
                ],
                keywords=["crash", "stability", "freeze", "unstable"]
            ),
            ComplaintCluster(
                id="cluster_2",
                analysis_id="test",
                name="Battery Drain",
                description="Excessive battery consumption",
                review_count=4,
                percentage=28.6,
                recency_score=75.0,
                sample_reviews=[
                    "This app drains my battery way too fast",
                    "Phone dies in 2 hours when using this app",
                    "Terrible battery optimization, needs fixing"
                ],
                keywords=["battery", "drain", "power", "optimization"]
            ),
            ComplaintCluster(
                id="cluster_3",
                analysis_id="test",
                name="UI/UX Issues",
                description="User interface and experience problems",
                review_count=4,
                percentage=28.6,
                recency_score=65.0,
                sample_reviews=[
                    "Interface is confusing and hard to navigate",
                    "Poor design choices make the app unusable",
                    "UI is outdated and not user-friendly"
                ],
                keywords=["ui", "interface", "design", "navigation", "ux"]
            ),
            ComplaintCluster(
                id="cluster_4",
                analysis_id="test",
                name="Performance Issues",
                description="Slow performance and loading times",
                review_count=3,
                percentage=21.4,
                recency_score=70.0,
                sample_reviews=[
                    "App is extremely slow and laggy",
                    "Takes forever to load anything",
                    "Performance has gotten worse with recent updates"
                ],
                keywords=["slow", "performance", "lag", "loading"]
            )
        ]
    
    def _create_website_review_dataset(self):
        """Create website review dataset from multiple platforms."""
        reviews = []
        
        # Google Reviews
        google_reviews = [
            "Poor customer service, waited 30 minutes",
            "Food was cold when it arrived",
            "Staff was rude and unprofessional"
        ]
        
        # Yelp Reviews
        yelp_reviews = [
            "Terrible experience, will not return",
            "Overpriced for the quality of food",
            "Restaurant was dirty and unkempt"
        ]
        
        # Facebook Reviews
        facebook_reviews = [
            "Disappointing meal, expected much better",
            "Service was extremely slow"
        ]
        
        platforms_data = [
            (google_reviews, Platform.GOOGLE_REVIEWS, "Google Reviews"),
            (yelp_reviews, Platform.YELP, "Yelp"),
            (facebook_reviews, Platform.FACEBOOK, "Facebook")
        ]
        
        review_id = 1
        for review_texts, platform, source in platforms_data:
            for text in review_texts:
                reviews.append(Review(
                    id=f"website_review_{review_id}",
                    website_url="https://myrestaurant.com",
                    platform=platform,
                    source_platform=source,
                    rating=2,
                    text=text,
                    review_date=datetime.now() - timedelta(days=review_id % 15),
                    locale="en_US"
                ))
                review_id += 1
        
        return reviews
    
    def _create_website_clusters(self):
        """Create website-specific complaint clusters."""
        return [
            ComplaintCluster(
                id="cluster_1",
                analysis_id="test",
                name="Service Issues",
                description="Poor customer service and staff behavior",
                review_count=4,
                percentage=50.0,
                recency_score=80.0,
                sample_reviews=[
                    "Poor customer service, waited 30 minutes",
                    "Staff was rude and unprofessional",
                    "Service was extremely slow"
                ],
                keywords=["service", "staff", "customer", "wait", "slow"]
            ),
            ComplaintCluster(
                id="cluster_2",
                analysis_id="test",
                name="Food Quality",
                description="Issues with food quality and temperature",
                review_count=3,
                percentage=37.5,
                recency_score=75.0,
                sample_reviews=[
                    "Food was cold when it arrived",
                    "Overpriced for the quality of food",
                    "Disappointing meal, expected much better"
                ],
                keywords=["food", "quality", "cold", "overpriced", "disappointing"]
            ),
            ComplaintCluster(
                id="cluster_3",
                analysis_id="test",
                name="Cleanliness",
                description="Restaurant cleanliness and hygiene concerns",
                review_count=1,
                percentage=12.5,
                recency_score=70.0,
                sample_reviews=[
                    "Restaurant was dirty and unkempt"
                ],
                keywords=["dirty", "cleanliness", "hygiene", "unkempt"]
            )
        ]
    
    def _create_large_review_dataset(self, count):
        """Create a large dataset for performance testing."""
        reviews = []
        complaint_types = [
            ("crashes", 1),
            ("battery drain", 2),
            ("slow performance", 2),
            ("UI issues", 1),
            ("bugs", 2)
        ]
        
        for i in range(count):
            complaint_type, rating = complaint_types[i % len(complaint_types)]
            reviews.append(Review(
                id=f"large_review_{i}",
                app_id="com.popular.app",
                platform=Platform.GOOGLE_PLAY,
                rating=rating,
                text=f"Review about {complaint_type} - review number {i}",
                review_date=datetime.now() - timedelta(days=i % 365),
                locale="en_US"
            ))
        
        return reviews
    
    def _create_many_clusters(self, count):
        """Create many clusters for performance testing."""
        clusters = []
        for i in range(count):
            clusters.append(ComplaintCluster(
                id=f"cluster_{i}",
                analysis_id="test",
                name=f"Issue Category {i}",
                description=f"Description for issue category {i}",
                review_count=250 - (i * 10),  # Decreasing counts
                percentage=max(1.0, 50.0 - (i * 2.5)),  # Decreasing percentages
                recency_score=max(10.0, 90.0 - (i * 4)),  # Decreasing recency
                sample_reviews=[f"Sample review for category {i}"],
                keywords=[f"keyword{i}", f"issue{i}"]
            ))
        
        return clusters
    
    def _update_analysis_status(self, analysis_id, status):
        """Update analysis status in database."""
        db = TestingSessionLocal()
        analysis = db.query(db_models.Analysis).filter_by(id=analysis_id).first()
        analysis.status = status
        db.commit()
        db.close()
    
    def _complete_analysis_with_results(self, analysis_id, reviews, clusters):
        """Complete analysis with results in database."""
        db = TestingSessionLocal()
        
        analysis = db.query(db_models.Analysis).filter_by(id=analysis_id).first()
        analysis.status = AnalysisStatus.COMPLETED
        analysis.completed_at = datetime.now()
        analysis.total_reviews = len(reviews)
        analysis.negative_reviews = len([r for r in reviews if r.rating <= 2])
        
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
    
    def _complete_website_analysis_with_results(self, analysis_id, reviews, clusters):
        """Complete website analysis with results in database."""
        db = TestingSessionLocal()
        
        analysis = db.query(db_models.Analysis).filter_by(id=analysis_id).first()
        analysis.status = AnalysisStatus.COMPLETED
        analysis.completed_at = datetime.now()
        analysis.total_reviews = len(reviews)
        analysis.negative_reviews = len([r for r in reviews if r.rating and r.rating <= 2])
        
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


if __name__ == "__main__":
    pytest.main([__file__])