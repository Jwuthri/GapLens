"""Comprehensive tests for database operations."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy.exc import IntegrityError

from app.models.database import Analysis, ComplaintCluster, Review
from app.models.schemas import Platform, AnalysisStatus


class TestDatabaseOperations:
    """Test database CRUD operations."""
    
    def test_create_analysis_record(self, test_session):
        """Test creating a new analysis record."""
        analysis = Analysis(
            app_id="com.test.app",
            analysis_type="APP",
            platform=Platform.GOOGLE_PLAY,
            status=AnalysisStatus.PENDING
        )
        
        test_session.add(analysis)
        test_session.commit()
        test_session.refresh(analysis)
        
        assert analysis.id is not None
        assert analysis.app_id == "com.test.app"
        assert analysis.platform == Platform.GOOGLE_PLAY
        assert analysis.status == AnalysisStatus.PENDING
        assert analysis.created_at is not None
    
    def test_create_website_analysis_record(self, test_session):
        """Test creating a website analysis record."""
        analysis = Analysis(
            website_url="https://example.com",
            analysis_type="WEBSITE",
            status=AnalysisStatus.PENDING
        )
        
        test_session.add(analysis)
        test_session.commit()
        test_session.refresh(analysis)
        
        assert analysis.id is not None
        assert analysis.website_url == "https://example.com"
        assert analysis.analysis_type == "WEBSITE"
        assert analysis.platform is None
    
    def test_create_review_record(self, test_session):
        """Test creating a review record."""
        review = Review(
            id="test_review_1",
            app_id="com.test.app",
            platform=Platform.GOOGLE_PLAY,
            rating=1,
            text="App crashes constantly",
            review_date=datetime.now(),
            locale="en_US"
        )
        
        test_session.add(review)
        test_session.commit()
        
        retrieved_review = test_session.query(Review).filter_by(id="test_review_1").first()
        assert retrieved_review is not None
        assert retrieved_review.text == "App crashes constantly"
        assert retrieved_review.rating == 1
    
    def test_create_website_review_record(self, test_session):
        """Test creating a website review record."""
        review = Review(
            id="website_review_1",
            website_url="https://example.com",
            platform=Platform.GOOGLE_REVIEWS,
            source_platform="Google Reviews",
            rating=2,
            text="Poor customer service",
            review_date=datetime.now(),
            locale="en_US"
        )
        
        test_session.add(review)
        test_session.commit()
        
        retrieved_review = test_session.query(Review).filter_by(id="website_review_1").first()
        assert retrieved_review is not None
        assert retrieved_review.website_url == "https://example.com"
        assert retrieved_review.source_platform == "Google Reviews"
    
    def test_create_complaint_cluster(self, test_session):
        """Test creating a complaint cluster."""
        # First create an analysis
        analysis = Analysis(
            app_id="com.test.app",
            analysis_type="APP",
            platform=Platform.GOOGLE_PLAY,
            status=AnalysisStatus.COMPLETED
        )
        test_session.add(analysis)
        test_session.commit()
        test_session.refresh(analysis)
        
        # Create cluster
        cluster = ComplaintCluster(
            analysis_id=analysis.id,
            name="Crash Issues",
            description="App crashes and stability problems",
            review_count=25,
            percentage=15.5,
            recency_score=85.2,
            sample_reviews=["App crashes on startup", "Constant crashes"],
            keywords=["crash", "stability", "bug"]
        )
        
        test_session.add(cluster)
        test_session.commit()
        test_session.refresh(cluster)
        
        assert cluster.id is not None
        assert cluster.analysis_id == analysis.id
        assert cluster.name == "Crash Issues"
        assert cluster.review_count == 25
        assert len(cluster.sample_reviews) == 2
        assert len(cluster.keywords) == 3
    
    def test_query_analysis_with_clusters(self, test_session):
        """Test querying analysis with related clusters."""
        # Create analysis
        analysis = Analysis(
            app_id="com.test.app",
            analysis_type="APP",
            platform=Platform.GOOGLE_PLAY,
            status=AnalysisStatus.COMPLETED,
            total_reviews=100,
            negative_reviews=30
        )
        test_session.add(analysis)
        test_session.commit()
        test_session.refresh(analysis)
        
        # Create multiple clusters
        clusters_data = [
            ("Crash Issues", 15, 50.0),
            ("Battery Drain", 10, 33.3),
            ("UI Problems", 5, 16.7)
        ]
        
        for name, count, percentage in clusters_data:
            cluster = ComplaintCluster(
                analysis_id=analysis.id,
                name=name,
                description=f"{name} description",
                review_count=count,
                percentage=percentage,
                recency_score=75.0,
                sample_reviews=[f"Sample review for {name}"],
                keywords=[name.lower().replace(" ", "_")]
            )
            test_session.add(cluster)
        
        test_session.commit()
        
        # Query analysis with clusters
        retrieved_analysis = test_session.query(Analysis).filter_by(id=analysis.id).first()
        assert retrieved_analysis is not None
        assert len(retrieved_analysis.clusters) == 3
        
        # Verify cluster data
        cluster_names = [cluster.name for cluster in retrieved_analysis.clusters]
        assert "Crash Issues" in cluster_names
        assert "Battery Drain" in cluster_names
        assert "UI Problems" in cluster_names
    
    def test_update_analysis_status(self, test_session):
        """Test updating analysis status."""
        analysis = Analysis(
            app_id="com.test.app",
            analysis_type="APP",
            platform=Platform.GOOGLE_PLAY,
            status=AnalysisStatus.PENDING
        )
        test_session.add(analysis)
        test_session.commit()
        test_session.refresh(analysis)
        
        # Update status
        analysis.status = AnalysisStatus.PROCESSING
        test_session.commit()
        
        # Verify update
        updated_analysis = test_session.query(Analysis).filter_by(id=analysis.id).first()
        assert updated_analysis.status == AnalysisStatus.PROCESSING
        
        # Complete analysis
        analysis.status = AnalysisStatus.COMPLETED
        analysis.completed_at = datetime.now()
        analysis.total_reviews = 150
        analysis.negative_reviews = 45
        test_session.commit()
        
        # Verify completion
        completed_analysis = test_session.query(Analysis).filter_by(id=analysis.id).first()
        assert completed_analysis.status == AnalysisStatus.COMPLETED
        assert completed_analysis.completed_at is not None
        assert completed_analysis.total_reviews == 150
        assert completed_analysis.negative_reviews == 45
    
    def test_delete_analysis_cascades_clusters(self, test_session):
        """Test that deleting analysis cascades to clusters."""
        # Create analysis with clusters
        analysis = Analysis(
            app_id="com.test.app",
            analysis_type="APP",
            platform=Platform.GOOGLE_PLAY,
            status=AnalysisStatus.COMPLETED
        )
        test_session.add(analysis)
        test_session.commit()
        test_session.refresh(analysis)
        
        # Add clusters
        for i in range(3):
            cluster = ComplaintCluster(
                analysis_id=analysis.id,
                name=f"Cluster {i}",
                description=f"Description {i}",
                review_count=10,
                percentage=33.3,
                recency_score=75.0,
                sample_reviews=[f"Sample {i}"],
                keywords=[f"keyword{i}"]
            )
            test_session.add(cluster)
        
        test_session.commit()
        
        # Verify clusters exist
        cluster_count = test_session.query(ComplaintCluster).filter_by(analysis_id=analysis.id).count()
        assert cluster_count == 3
        
        # Delete analysis
        test_session.delete(analysis)
        test_session.commit()
        
        # Verify clusters are deleted (cascade)
        remaining_clusters = test_session.query(ComplaintCluster).filter_by(analysis_id=analysis.id).count()
        assert remaining_clusters == 0
    
    def test_query_reviews_by_app_id(self, test_session):
        """Test querying reviews by app ID."""
        app_id = "com.test.app"
        
        # Create multiple reviews
        reviews_data = [
            ("review1", 1, "Crashes constantly"),
            ("review2", 2, "Battery drain issues"),
            ("review3", 1, "UI is confusing"),
            ("review4", 5, "Great app!")  # Positive review
        ]
        
        for review_id, rating, text in reviews_data:
            review = Review(
                id=review_id,
                app_id=app_id,
                platform=Platform.GOOGLE_PLAY,
                rating=rating,
                text=text,
                review_date=datetime.now(),
                locale="en_US"
            )
            test_session.add(review)
        
        test_session.commit()
        
        # Query all reviews for app
        all_reviews = test_session.query(Review).filter_by(app_id=app_id).all()
        assert len(all_reviews) == 4
        
        # Query only negative reviews (rating <= 2)
        negative_reviews = test_session.query(Review).filter(
            Review.app_id == app_id,
            Review.rating <= 2
        ).all()
        assert len(negative_reviews) == 3
    
    def test_query_reviews_by_date_range(self, test_session):
        """Test querying reviews by date range."""
        app_id = "com.test.app"
        now = datetime.now()
        
        # Create reviews with different dates
        reviews_data = [
            ("recent1", now - timedelta(days=1)),
            ("recent2", now - timedelta(days=5)),
            ("old1", now - timedelta(days=100)),
            ("old2", now - timedelta(days=200))
        ]
        
        for review_id, review_date in reviews_data:
            review = Review(
                id=review_id,
                app_id=app_id,
                platform=Platform.GOOGLE_PLAY,
                rating=1,
                text="Test review",
                review_date=review_date,
                locale="en_US"
            )
            test_session.add(review)
        
        test_session.commit()
        
        # Query recent reviews (last 30 days)
        cutoff_date = now - timedelta(days=30)
        recent_reviews = test_session.query(Review).filter(
            Review.app_id == app_id,
            Review.review_date >= cutoff_date
        ).all()
        
        assert len(recent_reviews) == 2
        
        # Query old reviews
        old_reviews = test_session.query(Review).filter(
            Review.app_id == app_id,
            Review.review_date < cutoff_date
        ).all()
        
        assert len(old_reviews) == 2
    
    def test_duplicate_review_handling(self, test_session):
        """Test handling of duplicate review IDs."""
        review1 = Review(
            id="duplicate_id",
            app_id="com.test.app",
            platform=Platform.GOOGLE_PLAY,
            rating=1,
            text="First review",
            review_date=datetime.now(),
            locale="en_US"
        )
        
        test_session.add(review1)
        test_session.commit()
        
        # Try to add duplicate
        review2 = Review(
            id="duplicate_id",  # Same ID
            app_id="com.test.app",
            platform=Platform.GOOGLE_PLAY,
            rating=2,
            text="Second review",
            review_date=datetime.now(),
            locale="en_US"
        )
        
        test_session.add(review2)
        
        # Should raise integrity error
        with pytest.raises(IntegrityError):
            test_session.commit()
    
    def test_analysis_without_required_fields(self, test_session):
        """Test creating analysis without required fields."""
        # Analysis without app_id or website_url should fail validation
        analysis = Analysis(
            analysis_type="APP",
            platform=Platform.GOOGLE_PLAY,
            status=AnalysisStatus.PENDING
        )
        
        test_session.add(analysis)
        
        # Should raise an error due to missing required fields
        with pytest.raises(Exception):  # Could be IntegrityError or ValidationError
            test_session.commit()
    
    def test_query_analysis_by_status(self, test_session):
        """Test querying analyses by status."""
        # Create analyses with different statuses
        statuses = [
            AnalysisStatus.PENDING,
            AnalysisStatus.PROCESSING,
            AnalysisStatus.COMPLETED,
            AnalysisStatus.FAILED
        ]
        
        for i, status in enumerate(statuses):
            analysis = Analysis(
                app_id=f"com.test.app{i}",
                analysis_type="APP",
                platform=Platform.GOOGLE_PLAY,
                status=status
            )
            test_session.add(analysis)
        
        test_session.commit()
        
        # Query by each status
        pending_count = test_session.query(Analysis).filter_by(status=AnalysisStatus.PENDING).count()
        processing_count = test_session.query(Analysis).filter_by(status=AnalysisStatus.PROCESSING).count()
        completed_count = test_session.query(Analysis).filter_by(status=AnalysisStatus.COMPLETED).count()
        failed_count = test_session.query(Analysis).filter_by(status=AnalysisStatus.FAILED).count()
        
        assert pending_count == 1
        assert processing_count == 1
        assert completed_count == 1
        assert failed_count == 1
    
    def test_cluster_ordering_by_percentage(self, test_session):
        """Test ordering clusters by percentage."""
        # Create analysis
        analysis = Analysis(
            app_id="com.test.app",
            analysis_type="APP",
            platform=Platform.GOOGLE_PLAY,
            status=AnalysisStatus.COMPLETED
        )
        test_session.add(analysis)
        test_session.commit()
        test_session.refresh(analysis)
        
        # Create clusters with different percentages
        clusters_data = [
            ("Low Impact", 5.0),
            ("High Impact", 45.0),
            ("Medium Impact", 25.0)
        ]
        
        for name, percentage in clusters_data:
            cluster = ComplaintCluster(
                analysis_id=analysis.id,
                name=name,
                description=f"{name} description",
                review_count=int(percentage),
                percentage=percentage,
                recency_score=75.0,
                sample_reviews=[f"Sample for {name}"],
                keywords=[name.lower().replace(" ", "_")]
            )
            test_session.add(cluster)
        
        test_session.commit()
        
        # Query clusters ordered by percentage (descending)
        ordered_clusters = test_session.query(ComplaintCluster).filter_by(
            analysis_id=analysis.id
        ).order_by(ComplaintCluster.percentage.desc()).all()
        
        assert len(ordered_clusters) == 3
        assert ordered_clusters[0].name == "High Impact"
        assert ordered_clusters[1].name == "Medium Impact"
        assert ordered_clusters[2].name == "Low Impact"


class TestDatabaseConstraints:
    """Test database constraints and validations."""
    
    def test_analysis_id_uniqueness(self, test_session):
        """Test that analysis IDs are unique."""
        analysis1 = Analysis(
            app_id="com.test.app1",
            analysis_type="APP",
            platform=Platform.GOOGLE_PLAY,
            status=AnalysisStatus.PENDING
        )
        
        analysis2 = Analysis(
            app_id="com.test.app2",
            analysis_type="APP",
            platform=Platform.APP_STORE,
            status=AnalysisStatus.PENDING
        )
        
        test_session.add(analysis1)
        test_session.add(analysis2)
        test_session.commit()
        
        # IDs should be different
        assert analysis1.id != analysis2.id
    
    def test_cluster_analysis_relationship(self, test_session):
        """Test cluster-analysis foreign key relationship."""
        # Create cluster without analysis (should fail)
        cluster = ComplaintCluster(
            analysis_id=uuid4(),  # Non-existent analysis ID
            name="Test Cluster",
            description="Test description",
            review_count=10,
            percentage=50.0,
            recency_score=75.0,
            sample_reviews=["Sample"],
            keywords=["test"]
        )
        
        test_session.add(cluster)
        
        # Should raise foreign key constraint error
        with pytest.raises(IntegrityError):
            test_session.commit()
    
    def test_review_platform_validation(self, test_session):
        """Test review platform field validation."""
        # Valid platforms should work
        valid_platforms = [Platform.GOOGLE_PLAY, Platform.APP_STORE, Platform.GOOGLE_REVIEWS]
        
        for i, platform in enumerate(valid_platforms):
            review = Review(
                id=f"test_review_{i}",
                app_id="com.test.app" if platform in [Platform.GOOGLE_PLAY, Platform.APP_STORE] else None,
                website_url="https://example.com" if platform == Platform.GOOGLE_REVIEWS else None,
                platform=platform,
                rating=1,
                text=f"Test review {i}",
                review_date=datetime.now(),
                locale="en_US"
            )
            test_session.add(review)
        
        test_session.commit()
        
        # Verify all reviews were created
        review_count = test_session.query(Review).count()
        assert review_count == len(valid_platforms)


if __name__ == "__main__":
    pytest.main([__file__])