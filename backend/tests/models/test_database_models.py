"""Tests for SQLAlchemy database models."""

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.database import Analysis, AnalysisStatus, ComplaintCluster, Platform, Review


class TestReviewModel:
    """Tests for the Review model."""
    
    def test_create_review(self, test_session, sample_review_data):
        """Test creating a review."""
        review = Review(
            id=sample_review_data["id"],
            app_id=sample_review_data["app_id"],
            platform=Platform.GOOGLE_PLAY,
            rating=sample_review_data["rating"],
            text=sample_review_data["text"],
            review_date=datetime.fromisoformat(sample_review_data["review_date"]),
            locale=sample_review_data["locale"]
        )
        
        test_session.add(review)
        test_session.commit()
        
        # Verify the review was created
        saved_review = test_session.query(Review).filter(Review.id == sample_review_data["id"]).first()
        assert saved_review is not None
        assert saved_review.app_id == sample_review_data["app_id"]
        assert saved_review.platform == Platform.GOOGLE_PLAY
        assert saved_review.rating == sample_review_data["rating"]
        assert saved_review.text == sample_review_data["text"]
        assert saved_review.locale == sample_review_data["locale"]
        assert saved_review.processed is False  # Default value
        assert saved_review.created_at is not None
    
    def test_review_required_fields(self, test_session):
        """Test that required fields are enforced."""
        # Missing required fields should raise an error
        with pytest.raises(IntegrityError):
            review = Review(
                # Missing id, app_id, platform, rating, text, review_date
            )
            test_session.add(review)
            test_session.commit()
    
    def test_review_platform_enum(self, test_session):
        """Test platform enum validation."""
        review = Review(
            id="test_review_enum",
            app_id="com.test.app",
            platform=Platform.APP_STORE,
            rating=2,
            text="Test review text",
            review_date=datetime.now()
        )
        
        test_session.add(review)
        test_session.commit()
        
        saved_review = test_session.query(Review).filter(Review.id == "test_review_enum").first()
        assert saved_review.platform == Platform.APP_STORE
    
    def test_review_rating_validation(self, test_session):
        """Test rating field accepts valid values."""
        for rating in [1, 2, 3, 4, 5]:
            review = Review(
                id=f"test_review_rating_{rating}",
                app_id="com.test.app",
                platform=Platform.GOOGLE_PLAY,
                rating=rating,
                text="Test review text",
                review_date=datetime.now()
            )
            
            test_session.add(review)
            test_session.commit()
            
            saved_review = test_session.query(Review).filter(Review.id == f"test_review_rating_{rating}").first()
            assert saved_review.rating == rating


class TestAnalysisModel:
    """Tests for the Analysis model."""
    
    def test_create_analysis(self, test_session, sample_analysis_data):
        """Test creating an analysis."""
        analysis = Analysis(
            app_id=sample_analysis_data["app_id"],
            analysis_type="APP",
            platform=Platform.GOOGLE_PLAY,
            status=AnalysisStatus.PENDING
        )
        
        test_session.add(analysis)
        test_session.commit()
        
        # Verify the analysis was created
        saved_analysis = test_session.query(Analysis).filter(Analysis.app_id == sample_analysis_data["app_id"]).first()
        assert saved_analysis is not None
        assert saved_analysis.id is not None  # UUID should be auto-generated
        assert saved_analysis.app_id == sample_analysis_data["app_id"]
        assert saved_analysis.platform == Platform.GOOGLE_PLAY
        assert saved_analysis.status == AnalysisStatus.PENDING
        assert saved_analysis.created_at is not None
        assert saved_analysis.completed_at is None
        assert saved_analysis.total_reviews is None
        assert saved_analysis.negative_reviews is None
    
    def test_analysis_status_enum(self, test_session):
        """Test analysis status enum values."""
        statuses = [AnalysisStatus.PENDING, AnalysisStatus.PROCESSING, AnalysisStatus.COMPLETED, AnalysisStatus.FAILED]
        
        for i, status in enumerate(statuses):
            analysis = Analysis(
                app_id=f"com.test.app_{i}",
                analysis_type="APP",
                platform=Platform.GOOGLE_PLAY,
                status=status
            )
            
            test_session.add(analysis)
            test_session.commit()
            
            saved_analysis = test_session.query(Analysis).filter(Analysis.app_id == f"com.test.app_{i}").first()
            assert saved_analysis.status == status
    
    def test_analysis_update_fields(self, test_session):
        """Test updating analysis fields."""
        analysis = Analysis(
            app_id="com.test.update",
            analysis_type="APP",
            platform=Platform.GOOGLE_PLAY,
            status=AnalysisStatus.PENDING
        )
        
        test_session.add(analysis)
        test_session.commit()
        
        # Update the analysis
        analysis.status = AnalysisStatus.COMPLETED
        analysis.total_reviews = 100
        analysis.negative_reviews = 25
        analysis.completed_at = datetime.now()
        
        test_session.commit()
        
        # Verify updates
        updated_analysis = test_session.query(Analysis).filter(Analysis.app_id == "com.test.update").first()
        assert updated_analysis.status == AnalysisStatus.COMPLETED
        assert updated_analysis.total_reviews == 100
        assert updated_analysis.negative_reviews == 25
        assert updated_analysis.completed_at is not None


class TestComplaintClusterModel:
    """Tests for the ComplaintCluster model."""
    
    def test_create_complaint_cluster(self, test_session, sample_cluster_data):
        """Test creating a complaint cluster."""
        # First create an analysis
        analysis = Analysis(
            app_id="com.test.cluster",
            analysis_type="APP",
            platform=Platform.GOOGLE_PLAY,
            status=AnalysisStatus.PROCESSING
        )
        test_session.add(analysis)
        test_session.commit()
        
        # Create complaint cluster
        cluster = ComplaintCluster(
            analysis_id=analysis.id,
            name=sample_cluster_data["name"],
            description=sample_cluster_data["description"],
            review_count=sample_cluster_data["review_count"],
            percentage=sample_cluster_data["percentage"],
            recency_score=sample_cluster_data["recency_score"],
            sample_reviews=sample_cluster_data["sample_reviews"],
            keywords=sample_cluster_data["keywords"]
        )
        
        test_session.add(cluster)
        test_session.commit()
        
        # Verify the cluster was created
        saved_cluster = test_session.query(ComplaintCluster).filter(ComplaintCluster.analysis_id == analysis.id).first()
        assert saved_cluster is not None
        assert saved_cluster.id is not None  # UUID should be auto-generated
        assert saved_cluster.analysis_id == analysis.id
        assert saved_cluster.name == sample_cluster_data["name"]
        assert saved_cluster.description == sample_cluster_data["description"]
        assert saved_cluster.review_count == sample_cluster_data["review_count"]
        assert float(saved_cluster.percentage) == sample_cluster_data["percentage"]
        assert float(saved_cluster.recency_score) == sample_cluster_data["recency_score"]
        assert saved_cluster.sample_reviews == sample_cluster_data["sample_reviews"]
        assert saved_cluster.keywords == sample_cluster_data["keywords"]
    
    def test_cluster_analysis_relationship(self, test_session):
        """Test the relationship between cluster and analysis."""
        # Create analysis
        analysis = Analysis(
            app_id="com.test.relationship",
            analysis_type="APP",
            platform=Platform.GOOGLE_PLAY,
            status=AnalysisStatus.PROCESSING
        )
        test_session.add(analysis)
        test_session.commit()
        
        # Create multiple clusters for the analysis
        cluster1 = ComplaintCluster(
            analysis_id=analysis.id,
            name="Cluster 1",
            review_count=10,
            percentage=20.0,
            recency_score=80.0
        )
        
        cluster2 = ComplaintCluster(
            analysis_id=analysis.id,
            name="Cluster 2", 
            review_count=15,
            percentage=30.0,
            recency_score=70.0
        )
        
        test_session.add_all([cluster1, cluster2])
        test_session.commit()
        
        # Test relationship access
        saved_analysis = test_session.query(Analysis).filter(Analysis.id == analysis.id).first()
        assert len(saved_analysis.clusters) == 2
        
        cluster_names = [cluster.name for cluster in saved_analysis.clusters]
        assert "Cluster 1" in cluster_names
        assert "Cluster 2" in cluster_names
        
        # Test back reference
        saved_cluster = test_session.query(ComplaintCluster).filter(ComplaintCluster.name == "Cluster 1").first()
        assert saved_cluster.analysis.id == analysis.id
        assert saved_cluster.analysis.app_id == "com.test.relationship"
    
    def test_cluster_cascade_delete(self, test_session):
        """Test that clusters are deleted when analysis is deleted."""
        # Create analysis with clusters
        analysis = Analysis(
            app_id="com.test.cascade",
            analysis_type="APP",
            platform=Platform.GOOGLE_PLAY,
            status=AnalysisStatus.COMPLETED
        )
        test_session.add(analysis)
        test_session.commit()
        
        cluster = ComplaintCluster(
            analysis_id=analysis.id,
            name="Test Cluster",
            review_count=5,
            percentage=10.0,
            recency_score=60.0
        )
        test_session.add(cluster)
        test_session.commit()
        
        # Verify cluster exists
        assert test_session.query(ComplaintCluster).filter(ComplaintCluster.analysis_id == analysis.id).count() == 1
        
        # Delete analysis
        test_session.delete(analysis)
        test_session.commit()
        
        # Verify cluster was also deleted (cascade)
        assert test_session.query(ComplaintCluster).filter(ComplaintCluster.analysis_id == analysis.id).count() == 0