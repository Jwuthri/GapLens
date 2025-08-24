"""Unit tests for clustering engine and insights generation."""

import pytest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from app.services.clustering_engine import ClusteringEngine, InsightsGenerator
from app.models.schemas import Review, Platform, ComplaintClusterBase


class TestClusteringEngine:
    """Test cases for the ClusteringEngine class."""
    
    @pytest.fixture
    def clustering_engine(self):
        """Create a clustering engine instance for testing."""
        return ClusteringEngine()
    
    @pytest.fixture
    def sample_reviews(self):
        """Create sample reviews for testing."""
        base_date = datetime.now()
        return [
            Review(
                id="1",
                app_id="test_app",
                platform=Platform.GOOGLE_PLAY,
                rating=1,
                text="App crashes constantly when I try to open it",
                review_date=base_date - timedelta(days=5),
                locale="en",
                processed=False,
                created_at=base_date
            ),
            Review(
                id="2",
                app_id="test_app",
                platform=Platform.GOOGLE_PLAY,
                rating=2,
                text="The app is very slow and takes forever to load",
                review_date=base_date - timedelta(days=10),
                locale="en",
                processed=False,
                created_at=base_date
            ),
            Review(
                id="3",
                app_id="test_app",
                platform=Platform.GOOGLE_PLAY,
                rating=1,
                text="Keeps crashing on my phone, unusable",
                review_date=base_date - timedelta(days=15),
                locale="en",
                processed=False,
                created_at=base_date
            ),
            Review(
                id="4",
                app_id="test_app",
                platform=Platform.GOOGLE_PLAY,
                rating=2,
                text="Performance is terrible, very laggy",
                review_date=base_date - timedelta(days=20),
                locale="en",
                processed=False,
                created_at=base_date
            ),
            Review(
                id="5",
                app_id="test_app",
                platform=Platform.GOOGLE_PLAY,
                rating=1,
                text="Battery drains too fast when using this app",
                review_date=base_date - timedelta(days=25),
                locale="en",
                processed=False,
                created_at=base_date
            )
        ]
    
    def test_initialization(self, clustering_engine):
        """Test clustering engine initialization."""
        assert clustering_engine is not None
        assert hasattr(clustering_engine, 'model_name')
        assert hasattr(clustering_engine, 'logger')
    
    def test_generate_embeddings_with_valid_texts(self, clustering_engine):
        """Test embedding generation with valid texts."""
        texts = [
            "App crashes constantly",
            "Very slow performance",
            "Battery drain issues"
        ]
        
        embeddings = clustering_engine.generate_embeddings(texts)
        
        assert isinstance(embeddings, np.ndarray)
        assert len(embeddings) == len(texts)
        if len(embeddings) > 0:
            assert embeddings.shape[1] > 0  # Should have some dimensions
    
    def test_generate_embeddings_with_empty_texts(self, clustering_engine):
        """Test embedding generation with empty texts."""
        texts = []
        embeddings = clustering_engine.generate_embeddings(texts)
        
        assert isinstance(embeddings, np.ndarray)
        assert len(embeddings) == 0
    
    def test_generate_embeddings_with_invalid_texts(self, clustering_engine):
        """Test embedding generation with invalid texts."""
        texts = ["", "   ", None]
        embeddings = clustering_engine.generate_embeddings(texts)
        
        # Should handle invalid texts gracefully
        assert isinstance(embeddings, np.ndarray)
    
    def test_find_optimal_clusters_insufficient_data(self, clustering_engine):
        """Test clustering with insufficient data."""
        embeddings = np.array([[1, 2], [3, 4]])  # Only 2 samples
        labels, algorithm = clustering_engine.find_optimal_clusters(embeddings, min_cluster_size=3)
        
        assert algorithm == "insufficient_data"
        assert len(labels) == 2
    
    def test_find_optimal_clusters_valid_data(self, clustering_engine):
        """Test clustering with valid data."""
        # Create mock embeddings that should cluster well
        embeddings = np.array([
            [1, 1], [1.1, 1.1], [1.2, 1.2],  # Cluster 1
            [5, 5], [5.1, 5.1], [5.2, 5.2],  # Cluster 2
            [10, 10], [10.1, 10.1], [10.2, 10.2]  # Cluster 3
        ])
        
        labels, algorithm = clustering_engine.find_optimal_clusters(embeddings, min_cluster_size=2)
        
        assert algorithm in ["hdbscan", "kmeans", "fallback"]
        assert len(labels) == len(embeddings)
        assert len(set(labels)) >= 1  # Should find at least one cluster
    
    def test_cluster_reviews_insufficient_reviews(self, clustering_engine):
        """Test clustering with insufficient reviews."""
        reviews = [
            Review(
                id="1",
                app_id="test",
                platform=Platform.GOOGLE_PLAY,
                rating=1,
                text="Short review",
                review_date=datetime.now(),
                locale="en",
                processed=False,
                created_at=datetime.now()
            )
        ]
        
        clusters = clustering_engine.cluster_reviews(reviews, min_cluster_size=3)
        assert len(clusters) == 0
    
    def test_cluster_reviews_valid_data(self, clustering_engine, sample_reviews):
        """Test clustering with valid review data."""
        clusters = clustering_engine.cluster_reviews(sample_reviews, min_cluster_size=2)
        
        # Should create some clusters
        assert isinstance(clusters, list)
        
        # If clusters are created, validate their structure
        for cluster in clusters:
            assert isinstance(cluster, ComplaintClusterBase)
            assert cluster.name is not None
            assert cluster.review_count > 0
            assert 0 <= cluster.percentage <= 100
            assert 0 <= cluster.recency_score <= 100
            assert isinstance(cluster.sample_reviews, list)
            assert isinstance(cluster.keywords, list)
    
    def test_clean_text_for_clustering(self, clustering_engine):
        """Test text cleaning for clustering."""
        text = "This app CRASHES!!! Visit http://example.com for help. Email: test@example.com"
        cleaned = clustering_engine._clean_text_for_clustering(text)
        
        assert "http://example.com" not in cleaned
        assert "test@example.com" not in cleaned
        assert cleaned.lower() == cleaned  # Should be lowercase
        assert "crashes" in cleaned.lower()
    
    def test_extract_cluster_keywords(self, clustering_engine):
        """Test keyword extraction from cluster texts."""
        texts = [
            "App crashes constantly on startup",
            "Crashing issues with the application",
            "Frequent crashes make app unusable"
        ]
        
        keywords = clustering_engine._extract_cluster_keywords(texts)
        
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        # Should contain crash-related keywords
        crash_keywords = [kw for kw in keywords if 'crash' in kw.lower()]
        assert len(crash_keywords) > 0
    
    def test_generate_cluster_name_and_description(self, clustering_engine):
        """Test cluster name and description generation."""
        keywords = ["crash", "startup", "error"]
        texts = ["App crashes on startup", "Startup error occurs"]
        
        name, description = clustering_engine._generate_cluster_name_and_description(keywords, texts)
        
        assert isinstance(name, str)
        assert isinstance(description, str)
        assert len(name) > 0
        assert len(description) > 0
        assert "crash" in name.lower() or "crash" in description.lower()
    
    def test_calculate_recency_score(self, clustering_engine):
        """Test recency score calculation."""
        now = datetime.now()
        reviews = [
            Mock(review_date=now - timedelta(days=5)),   # Very recent
            Mock(review_date=now - timedelta(days=30)),  # Recent
            Mock(review_date=now - timedelta(days=120))  # Old
        ]
        
        score = clustering_engine._calculate_recency_score(reviews)
        
        assert 0 <= score <= 100
        assert isinstance(score, float)
    
    def test_rank_clusters_by_importance(self, clustering_engine):
        """Test cluster ranking by importance."""
        clusters = [
            ComplaintClusterBase(
                name="Low Priority",
                review_count=5,
                percentage=10.0,
                recency_score=20.0,
                sample_reviews=["test"],
                keywords=["test"]
            ),
            ComplaintClusterBase(
                name="High Priority",
                review_count=20,
                percentage=40.0,
                recency_score=80.0,
                sample_reviews=["test"],
                keywords=["test"]
            ),
            ComplaintClusterBase(
                name="Medium Priority",
                review_count=10,
                percentage=20.0,
                recency_score=50.0,
                sample_reviews=["test"],
                keywords=["test"]
            )
        ]
        
        ranked_clusters = clustering_engine._rank_clusters_by_importance(clusters)
        
        assert len(ranked_clusters) == 3
        # Should be sorted by importance (combination of frequency and recency)
        # High Priority should be first due to high percentage and recency
        assert ranked_clusters[0].name == "High Priority"


class TestInsightsGenerator:
    """Test cases for the InsightsGenerator class."""
    
    @pytest.fixture
    def insights_generator(self):
        """Create an insights generator instance for testing."""
        return InsightsGenerator()
    
    @pytest.fixture
    def sample_clusters(self):
        """Create sample clusters for testing."""
        return [
            ComplaintClusterBase(
                name="App Crashes",
                description="Issues with app stability",
                review_count=15,
                percentage=30.0,
                recency_score=75.0,
                sample_reviews=["App crashes on startup", "Frequent crashes"],
                keywords=["crash", "startup", "error"]
            ),
            ComplaintClusterBase(
                name="Performance Issues",
                description="Slow performance complaints",
                review_count=10,
                percentage=20.0,
                recency_score=50.0,
                sample_reviews=["Very slow", "Takes forever to load"],
                keywords=["slow", "performance", "lag"]
            ),
            ComplaintClusterBase(
                name="Battery Drain",
                description="Battery consumption issues",
                review_count=8,
                percentage=16.0,
                recency_score=30.0,
                sample_reviews=["Battery drains fast"],
                keywords=["battery", "drain", "power"]
            )
        ]
    
    def test_generate_summary_insights_empty_data(self, insights_generator):
        """Test insights generation with empty data."""
        insights = insights_generator.generate_summary_insights([], [])
        
        assert insights['total_reviews'] == 0
        assert insights['clustered_reviews'] == 0
        assert insights['coverage_percentage'] == 0
        assert insights['top_issues'] == []
        assert isinstance(insights['recommendations'], list)
    
    def test_generate_summary_insights_valid_data(self, insights_generator, sample_reviews, sample_clusters):
        """Test insights generation with valid data."""
        insights = insights_generator.generate_summary_insights(sample_reviews, sample_clusters)
        
        assert insights['total_reviews'] == len(sample_reviews)
        assert insights['clustered_reviews'] > 0
        assert 0 <= insights['coverage_percentage'] <= 100
        assert len(insights['top_issues']) <= 5
        assert isinstance(insights['trend_analysis'], dict)
        assert isinstance(insights['recommendations'], list)
        assert len(insights['recommendations']) > 0
    
    def test_analyze_trends(self, insights_generator, sample_reviews):
        """Test trend analysis functionality."""
        # Create a mix of recent and old reviews
        now = datetime.now()
        recent_reviews = [
            Mock(review_date=now - timedelta(days=5)),
            Mock(review_date=now - timedelta(days=10))
        ]
        old_reviews = [
            Mock(review_date=now - timedelta(days=60)),
            Mock(review_date=now - timedelta(days=90))
        ]
        all_reviews = recent_reviews + old_reviews
        
        trends = insights_generator._analyze_trends(all_reviews, [])
        
        assert 'recent_activity' in trends
        assert 'trend_direction' in trends
        assert trends['trend_direction'] in ['increasing', 'decreasing', 'stable']
        assert 0 <= trends['recent_activity'] <= 100
    
    def test_generate_recommendations_empty_clusters(self, insights_generator):
        """Test recommendation generation with empty clusters."""
        recommendations = insights_generator._generate_recommendations([])
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        assert "Insufficient data" in recommendations[0]
    
    def test_generate_recommendations_valid_clusters(self, insights_generator, sample_clusters):
        """Test recommendation generation with valid clusters."""
        recommendations = insights_generator._generate_recommendations(sample_clusters)
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        
        # Should contain actionable recommendations
        recommendation_text = ' '.join(recommendations).lower()
        assert any(word in recommendation_text for word in ['priority', 'address', 'focus', 'monitor'])


class TestIntegration:
    """Integration tests for clustering and insights together."""
    
    @pytest.fixture
    def full_pipeline(self):
        """Create full pipeline with clustering and insights."""
        clustering_engine = ClusteringEngine()
        insights_generator = InsightsGenerator()
        return clustering_engine, insights_generator
    
    def test_full_clustering_and_insights_pipeline(self, full_pipeline, sample_reviews):
        """Test the complete pipeline from reviews to insights."""
        clustering_engine, insights_generator = full_pipeline
        
        # Cluster the reviews
        clusters = clustering_engine.cluster_reviews(sample_reviews, min_cluster_size=2)
        
        # Generate insights
        insights = insights_generator.generate_summary_insights(sample_reviews, clusters)
        
        # Validate the complete pipeline
        assert isinstance(clusters, list)
        assert isinstance(insights, dict)
        
        # Check that insights contain expected keys
        expected_keys = ['total_reviews', 'clustered_reviews', 'coverage_percentage', 
                        'top_issues', 'trend_analysis', 'recommendations']
        for key in expected_keys:
            assert key in insights
        
        # Validate data consistency
        assert insights['total_reviews'] == len(sample_reviews)
        if clusters:
            assert insights['clustered_reviews'] > 0
            assert len(insights['top_issues']) > 0


# Fixtures for all tests
@pytest.fixture
def sample_reviews():
    """Create sample reviews for testing."""
    base_date = datetime.now()
    return [
        Review(
            id="1",
            app_id="test_app",
            platform=Platform.GOOGLE_PLAY,
            rating=1,
            text="App crashes constantly when I try to open it",
            review_date=base_date - timedelta(days=5),
            locale="en",
            processed=False,
            created_at=base_date
        ),
        Review(
            id="2",
            app_id="test_app",
            platform=Platform.GOOGLE_PLAY,
            rating=2,
            text="The app is very slow and takes forever to load",
            review_date=base_date - timedelta(days=10),
            locale="en",
            processed=False,
            created_at=base_date
        ),
        Review(
            id="3",
            app_id="test_app",
            platform=Platform.GOOGLE_PLAY,
            rating=1,
            text="Keeps crashing on my phone, unusable",
            review_date=base_date - timedelta(days=15),
            locale="en",
            processed=False,
            created_at=base_date
        ),
        Review(
            id="4",
            app_id="test_app",
            platform=Platform.GOOGLE_PLAY,
            rating=2,
            text="Performance is terrible, very laggy",
            review_date=base_date - timedelta(days=20),
            locale="en",
            processed=False,
            created_at=base_date
        ),
        Review(
            id="5",
            app_id="test_app",
            platform=Platform.GOOGLE_PLAY,
            rating=1,
            text="Battery drains too fast when using this app",
            review_date=base_date - timedelta(days=25),
            locale="en",
            processed=False,
            created_at=base_date
        )
    ]