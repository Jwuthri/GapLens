"""Comprehensive tests for clustering engine service."""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from app.services.clustering_engine import ClusteringEngine
from app.models.schemas import Review, ComplaintCluster, Platform


class TestClusteringEngine:
    """Test cases for ClusteringEngine class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ClusteringEngine()
        self.sample_reviews = [
            Review(
                id="1",
                app_id="com.test.app",
                platform=Platform.GOOGLE_PLAY,
                rating=1,
                text="App crashes constantly on startup",
                review_date=datetime.now() - timedelta(days=1),
                locale="en_US"
            ),
            Review(
                id="2",
                app_id="com.test.app",
                platform=Platform.GOOGLE_PLAY,
                rating=2,
                text="Battery drain is terrible, phone dies quickly",
                review_date=datetime.now() - timedelta(days=2),
                locale="en_US"
            ),
            Review(
                id="3",
                app_id="com.test.app",
                platform=Platform.GOOGLE_PLAY,
                rating=1,
                text="Crashes every time I try to open it",
                review_date=datetime.now() - timedelta(days=3),
                locale="en_US"
            ),
            Review(
                id="4",
                app_id="com.test.app",
                platform=Platform.GOOGLE_PLAY,
                rating=2,
                text="Drains battery way too fast",
                review_date=datetime.now() - timedelta(days=5),
                locale="en_US"
            ),
            Review(
                id="5",
                app_id="com.test.app",
                platform=Platform.GOOGLE_PLAY,
                rating=1,
                text="Needs offline mode, can't use without internet",
                review_date=datetime.now() - timedelta(days=10),
                locale="en_US"
            )
        ]
    
    @patch('app.services.clustering_engine.SentenceTransformer')
    def test_generate_embeddings_success(self, mock_transformer):
        """Test successful embedding generation."""
        # Mock the transformer
        mock_model = Mock()
        mock_model.encode.return_value = np.array([
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
            [0.7, 0.8, 0.9]
        ])
        mock_transformer.return_value = mock_model
        
        texts = ["text1", "text2", "text3"]
        embeddings = self.engine.generate_embeddings(texts)
        
        assert embeddings.shape == (3, 3)
        mock_model.encode.assert_called_once_with(texts, show_progress_bar=False)
    
    @patch('app.services.clustering_engine.SentenceTransformer')
    def test_generate_embeddings_empty_input(self, mock_transformer):
        """Test embedding generation with empty input."""
        embeddings = self.engine.generate_embeddings([])
        
        assert embeddings.shape == (0, 0)
        mock_transformer.assert_not_called()
    
    @patch('app.services.clustering_engine.HDBSCAN')
    def test_cluster_reviews_hdbscan_success(self, mock_hdbscan):
        """Test successful clustering with HDBSCAN."""
        # Mock HDBSCAN
        mock_clusterer = Mock()
        mock_clusterer.fit_predict.return_value = np.array([0, 0, 1, 1, -1])
        mock_clusterer.labels_ = np.array([0, 0, 1, 1, -1])
        mock_hdbscan.return_value = mock_clusterer
        
        # Mock embedding generation
        with patch.object(self.engine, 'generate_embeddings') as mock_embeddings:
            mock_embeddings.return_value = np.random.rand(5, 384)
            
            clusters = self.engine.cluster_reviews(self.sample_reviews)
            
            assert len(clusters) == 2  # Two clusters (excluding noise)
            assert all(isinstance(cluster, ComplaintCluster) for cluster in clusters)
            mock_hdbscan.assert_called_once()
    
    @patch('app.services.clustering_engine.KMeans')
    def test_cluster_reviews_kmeans_fallback(self, mock_kmeans):
        """Test clustering fallback to KMeans when HDBSCAN fails."""
        # Mock KMeans
        mock_clusterer = Mock()
        mock_clusterer.fit_predict.return_value = np.array([0, 0, 1, 1, 0])
        mock_clusterer.labels_ = np.array([0, 0, 1, 1, 0])
        mock_kmeans.return_value = mock_clusterer
        
        # Mock HDBSCAN to raise exception
        with patch('app.services.clustering_engine.HDBSCAN') as mock_hdbscan:
            mock_hdbscan.side_effect = Exception("HDBSCAN failed")
            
            # Mock embedding generation
            with patch.object(self.engine, 'generate_embeddings') as mock_embeddings:
                mock_embeddings.return_value = np.random.rand(5, 384)
                
                clusters = self.engine.cluster_reviews(self.sample_reviews)
                
                assert len(clusters) == 2
                mock_kmeans.assert_called_once()
    
    def test_cluster_reviews_insufficient_data(self):
        """Test clustering with insufficient data."""
        single_review = [self.sample_reviews[0]]
        
        clusters = self.engine.cluster_reviews(single_review)
        
        assert len(clusters) == 1
        assert clusters[0].name == "General Issues"
        assert clusters[0].review_count == 1
    
    def test_generate_cluster_name_with_keywords(self):
        """Test cluster name generation with keywords."""
        review_texts = [
            "App crashes constantly",
            "Crashes on startup",
            "Crashing issues"
        ]
        
        name = self.engine.generate_cluster_name(review_texts)
        
        assert "crash" in name.lower() or "stability" in name.lower()
        assert len(name) > 0
    
    def test_generate_cluster_name_empty_input(self):
        """Test cluster name generation with empty input."""
        name = self.engine.generate_cluster_name([])
        
        assert name == "General Issues"
    
    def test_extract_keywords_success(self):
        """Test keyword extraction from review texts."""
        texts = [
            "App crashes constantly on startup",
            "Battery drain is terrible",
            "Crashes every time"
        ]
        
        keywords = self.engine.extract_keywords(texts)
        
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        assert all(isinstance(keyword, str) for keyword in keywords)
    
    def test_extract_keywords_empty_input(self):
        """Test keyword extraction with empty input."""
        keywords = self.engine.extract_keywords([])
        
        assert keywords == []
    
    def test_calculate_recency_score_recent_reviews(self):
        """Test recency score calculation for recent reviews."""
        recent_dates = [
            datetime.now() - timedelta(days=1),
            datetime.now() - timedelta(days=2),
            datetime.now() - timedelta(days=3)
        ]
        
        score = self.engine.calculate_recency_score(recent_dates)
        
        assert 80 <= score <= 100  # Recent reviews should have high score
    
    def test_calculate_recency_score_old_reviews(self):
        """Test recency score calculation for old reviews."""
        old_dates = [
            datetime.now() - timedelta(days=180),
            datetime.now() - timedelta(days=200),
            datetime.now() - timedelta(days=220)
        ]
        
        score = self.engine.calculate_recency_score(old_dates)
        
        assert 0 <= score <= 30  # Old reviews should have low score
    
    def test_calculate_recency_score_mixed_dates(self):
        """Test recency score calculation for mixed date ranges."""
        mixed_dates = [
            datetime.now() - timedelta(days=1),
            datetime.now() - timedelta(days=30),
            datetime.now() - timedelta(days=90),
            datetime.now() - timedelta(days=180)
        ]
        
        score = self.engine.calculate_recency_score(mixed_dates)
        
        assert 30 <= score <= 80  # Mixed dates should have medium score
    
    def test_calculate_recency_score_empty_dates(self):
        """Test recency score calculation with empty dates."""
        score = self.engine.calculate_recency_score([])
        
        assert score == 0.0
    
    def test_rank_clusters_by_frequency_and_recency(self):
        """Test cluster ranking by frequency and recency."""
        clusters = [
            ComplaintCluster(
                id="1",
                analysis_id="test",
                name="Crash Issues",
                description="App crashes",
                review_count=20,
                percentage=40.0,
                recency_score=90.0,
                sample_reviews=["crash1", "crash2"],
                keywords=["crash"]
            ),
            ComplaintCluster(
                id="2",
                analysis_id="test",
                name="Battery Issues",
                description="Battery drain",
                review_count=15,
                percentage=30.0,
                recency_score=60.0,
                sample_reviews=["battery1", "battery2"],
                keywords=["battery"]
            ),
            ComplaintCluster(
                id="3",
                analysis_id="test",
                name="UI Issues",
                description="Interface problems",
                review_count=10,
                percentage=20.0,
                recency_score=95.0,
                sample_reviews=["ui1", "ui2"],
                keywords=["ui"]
            )
        ]
        
        ranked_clusters = self.engine.rank_clusters(clusters)
        
        # Should be ranked by combined score (frequency + recency)
        assert len(ranked_clusters) == 3
        assert ranked_clusters[0].name == "Crash Issues"  # High frequency + high recency
    
    def test_rank_clusters_empty_input(self):
        """Test cluster ranking with empty input."""
        ranked_clusters = self.engine.rank_clusters([])
        
        assert ranked_clusters == []
    
    def test_get_sample_reviews_sufficient_reviews(self):
        """Test getting sample reviews when sufficient reviews available."""
        review_texts = [
            "Review 1 text",
            "Review 2 text",
            "Review 3 text",
            "Review 4 text",
            "Review 5 text"
        ]
        
        samples = self.engine.get_sample_reviews(review_texts, max_samples=3)
        
        assert len(samples) == 3
        assert all(sample in review_texts for sample in samples)
    
    def test_get_sample_reviews_insufficient_reviews(self):
        """Test getting sample reviews when insufficient reviews available."""
        review_texts = ["Review 1", "Review 2"]
        
        samples = self.engine.get_sample_reviews(review_texts, max_samples=5)
        
        assert len(samples) == 2
        assert samples == review_texts
    
    def test_get_sample_reviews_empty_input(self):
        """Test getting sample reviews with empty input."""
        samples = self.engine.get_sample_reviews([], max_samples=3)
        
        assert samples == []
    
    @patch('app.services.clustering_engine.SentenceTransformer')
    @patch('app.services.clustering_engine.HDBSCAN')
    def test_full_clustering_pipeline(self, mock_hdbscan, mock_transformer):
        """Test the complete clustering pipeline."""
        # Mock transformer
        mock_model = Mock()
        mock_model.encode.return_value = np.random.rand(5, 384)
        mock_transformer.return_value = mock_model
        
        # Mock HDBSCAN
        mock_clusterer = Mock()
        mock_clusterer.fit_predict.return_value = np.array([0, 0, 1, 1, -1])
        mock_clusterer.labels_ = np.array([0, 0, 1, 1, -1])
        mock_hdbscan.return_value = mock_clusterer
        
        clusters = self.engine.cluster_reviews(self.sample_reviews)
        
        # Verify pipeline execution
        assert len(clusters) == 2
        for cluster in clusters:
            assert cluster.name is not None
            assert cluster.review_count > 0
            assert cluster.percentage > 0
            assert cluster.recency_score >= 0
            assert len(cluster.sample_reviews) > 0
            assert len(cluster.keywords) >= 0
    
    def test_clustering_with_single_cluster(self):
        """Test clustering when all reviews belong to single cluster."""
        similar_reviews = [
            Review(
                id=str(i),
                app_id="com.test.app",
                platform=Platform.GOOGLE_PLAY,
                rating=1,
                text=f"App crashes on startup {i}",
                review_date=datetime.now() - timedelta(days=i),
                locale="en_US"
            )
            for i in range(1, 6)
        ]
        
        with patch.object(self.engine, 'generate_embeddings') as mock_embeddings:
            mock_embeddings.return_value = np.random.rand(5, 384)
            
            with patch('app.services.clustering_engine.HDBSCAN') as mock_hdbscan:
                mock_clusterer = Mock()
                mock_clusterer.fit_predict.return_value = np.array([0, 0, 0, 0, 0])
                mock_clusterer.labels_ = np.array([0, 0, 0, 0, 0])
                mock_hdbscan.return_value = mock_clusterer
                
                clusters = self.engine.cluster_reviews(similar_reviews)
                
                assert len(clusters) == 1
                assert clusters[0].review_count == 5
                assert clusters[0].percentage == 100.0
    
    def test_clustering_with_all_noise(self):
        """Test clustering when all reviews are classified as noise."""
        with patch.object(self.engine, 'generate_embeddings') as mock_embeddings:
            mock_embeddings.return_value = np.random.rand(5, 384)
            
            with patch('app.services.clustering_engine.HDBSCAN') as mock_hdbscan:
                mock_clusterer = Mock()
                mock_clusterer.fit_predict.return_value = np.array([-1, -1, -1, -1, -1])
                mock_clusterer.labels_ = np.array([-1, -1, -1, -1, -1])
                mock_hdbscan.return_value = mock_clusterer
                
                clusters = self.engine.cluster_reviews(self.sample_reviews)
                
                # Should create a single "General Issues" cluster
                assert len(clusters) == 1
                assert clusters[0].name == "General Issues"
                assert clusters[0].review_count == 5


class TestClusteringEngineEdgeCases:
    """Test edge cases and error handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ClusteringEngine()
    
    def test_clustering_with_very_long_reviews(self):
        """Test clustering with very long review texts."""
        long_text = "This is a very long review text. " * 100  # ~3400 characters
        
        long_reviews = [
            Review(
                id="1",
                app_id="com.test.app",
                platform=Platform.GOOGLE_PLAY,
                rating=1,
                text=long_text,
                review_date=datetime.now(),
                locale="en_US"
            )
        ]
        
        # Should handle long text without errors
        clusters = self.engine.cluster_reviews(long_reviews)
        assert len(clusters) == 1
    
    def test_clustering_with_special_characters(self):
        """Test clustering with special characters in reviews."""
        special_reviews = [
            Review(
                id="1",
                app_id="com.test.app",
                platform=Platform.GOOGLE_PLAY,
                rating=1,
                text="App crashes! @#$%^&*()_+ 😡😡😡",
                review_date=datetime.now(),
                locale="en_US"
            ),
            Review(
                id="2",
                app_id="com.test.app",
                platform=Platform.GOOGLE_PLAY,
                rating=2,
                text="Battery drain... 🔋💀 ¿Por qué?",
                review_date=datetime.now(),
                locale="es_ES"
            )
        ]
        
        clusters = self.engine.cluster_reviews(special_reviews)
        assert len(clusters) >= 1
    
    def test_clustering_with_empty_review_texts(self):
        """Test clustering with empty or whitespace-only review texts."""
        empty_reviews = [
            Review(
                id="1",
                app_id="com.test.app",
                platform=Platform.GOOGLE_PLAY,
                rating=1,
                text="",
                review_date=datetime.now(),
                locale="en_US"
            ),
            Review(
                id="2",
                app_id="com.test.app",
                platform=Platform.GOOGLE_PLAY,
                rating=2,
                text="   ",
                review_date=datetime.now(),
                locale="en_US"
            )
        ]
        
        # Should handle empty texts gracefully
        clusters = self.engine.cluster_reviews(empty_reviews)
        assert isinstance(clusters, list)
    
    @patch('app.services.clustering_engine.SentenceTransformer')
    def test_embedding_generation_failure(self, mock_transformer):
        """Test handling of embedding generation failure."""
        mock_transformer.side_effect = Exception("Model loading failed")
        
        # Should handle embedding failure gracefully
        with pytest.raises(Exception):
            self.engine.generate_embeddings(["test text"])
    
    def test_clustering_performance_with_large_dataset(self):
        """Test clustering performance with large number of reviews."""
        # Create 100 reviews
        large_dataset = [
            Review(
                id=str(i),
                app_id="com.test.app",
                platform=Platform.GOOGLE_PLAY,
                rating=1 if i % 2 == 0 else 2,
                text=f"Review text number {i} with some complaint content",
                review_date=datetime.now() - timedelta(days=i % 30),
                locale="en_US"
            )
            for i in range(100)
        ]
        
        with patch.object(self.engine, 'generate_embeddings') as mock_embeddings:
            mock_embeddings.return_value = np.random.rand(100, 384)
            
            with patch('app.services.clustering_engine.HDBSCAN') as mock_hdbscan:
                mock_clusterer = Mock()
                # Create multiple clusters
                labels = np.array([i % 5 for i in range(100)])  # 5 clusters
                mock_clusterer.fit_predict.return_value = labels
                mock_clusterer.labels_ = labels
                mock_hdbscan.return_value = mock_clusterer
                
                clusters = self.engine.cluster_reviews(large_dataset)
                
                assert len(clusters) == 5
                total_reviews = sum(cluster.review_count for cluster in clusters)
                assert total_reviews == 100


if __name__ == "__main__":
    pytest.main([__file__])