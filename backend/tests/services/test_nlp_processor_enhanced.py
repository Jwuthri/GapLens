"""Enhanced unit tests for NLP processor with clustering integration."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from app.services.nlp_processor import NLPProcessor
from app.models.schemas import Review, Platform, ComplaintClusterBase


class TestNLPProcessorEnhanced:
    """Test cases for enhanced NLP processor with clustering integration."""
    
    @pytest.fixture
    def nlp_processor(self):
        """Create an NLP processor instance for testing."""
        return NLPProcessor()
    
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
                text="App crashes constantly when I try to open it. Very frustrating!",
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
                text="The app is very slow and takes forever to load pages",
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
                text="Keeps crashing on my Android phone, completely unusable",
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
                text="Performance is terrible, very laggy and unresponsive",
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
                text="Battery drains too fast when using this app for more than 10 minutes",
                review_date=base_date - timedelta(days=25),
                locale="en",
                processed=False,
                created_at=base_date
            ),
            Review(
                id="6",
                app_id="test_app",
                platform=Platform.GOOGLE_PLAY,
                rating=4,  # Positive review - should be filtered out
                text="Great app, works perfectly fine for me",
                review_date=base_date - timedelta(days=30),
                locale="en",
                processed=False,
                created_at=base_date
            )
        ]
    
    def test_initialization_with_clustering_engine(self, nlp_processor):
        """Test that NLP processor initializes with clustering engine."""
        assert hasattr(nlp_processor, 'clustering_engine')
        assert hasattr(nlp_processor, 'insights_generator')
        assert nlp_processor.clustering_engine is not None
        assert nlp_processor.insights_generator is not None
    
    def test_process_reviews_integration(self, nlp_processor, sample_reviews):
        """Test the complete review processing pipeline."""
        processed_reviews = nlp_processor.process_reviews(sample_reviews)
        
        # Should filter out positive reviews
        assert len(processed_reviews) < len(sample_reviews)
        
        # All processed reviews should be negative
        for review in processed_reviews:
            assert review.rating is None or review.rating <= 2
        
        # Should not contain the positive review
        positive_review_ids = [r.id for r in processed_reviews if r.rating and r.rating > 2]
        assert len(positive_review_ids) == 0
    
    def test_cluster_complaints_integration(self, nlp_processor, sample_reviews):
        """Test clustering integration with the enhanced engine."""
        # First process reviews to get negative ones
        processed_reviews = nlp_processor.process_reviews(sample_reviews)
        
        # Then cluster them
        clusters = nlp_processor.cluster_complaints(processed_reviews, min_cluster_size=2)
        
        # Validate clustering results
        assert isinstance(clusters, list)
        
        # If clusters are created, validate their structure
        for cluster in clusters:
            assert isinstance(cluster, ComplaintClusterBase)
            assert cluster.name is not None
            assert len(cluster.name) > 0
            assert cluster.review_count > 0
            assert 0 <= cluster.percentage <= 100
            assert 0 <= cluster.recency_score <= 100
            assert isinstance(cluster.sample_reviews, list)
            assert len(cluster.sample_reviews) > 0
            assert isinstance(cluster.keywords, list)
            assert len(cluster.keywords) > 0
    
    def test_generate_insights_integration(self, nlp_processor, sample_reviews):
        """Test insights generation integration."""
        # Process and cluster reviews
        processed_reviews = nlp_processor.process_reviews(sample_reviews)
        clusters = nlp_processor.cluster_complaints(processed_reviews, min_cluster_size=2)
        
        # Generate insights
        insights = nlp_processor.generate_insights(processed_reviews, clusters)
        
        # Validate insights structure
        assert isinstance(insights, dict)
        
        expected_keys = [
            'total_reviews', 'clustered_reviews', 'coverage_percentage',
            'top_issues', 'trend_analysis', 'recommendations'
        ]
        
        for key in expected_keys:
            assert key in insights
        
        # Validate insights content
        assert insights['total_reviews'] == len(processed_reviews)
        assert isinstance(insights['top_issues'], list)
        assert isinstance(insights['trend_analysis'], dict)
        assert isinstance(insights['recommendations'], list)
        assert len(insights['recommendations']) > 0
    
    def test_clustering_accuracy_with_similar_complaints(self, nlp_processor):
        """Test clustering accuracy with clearly similar complaints."""
        base_date = datetime.now()
        
        # Create reviews with clear complaint categories
        crash_reviews = [
            Review(
                id=f"crash_{i}",
                app_id="test_app",
                platform=Platform.GOOGLE_PLAY,
                rating=1,
                text=text,
                review_date=base_date - timedelta(days=i),
                locale="en",
                processed=False,
                created_at=base_date
            )
            for i, text in enumerate([
                "App crashes when I open it",
                "Constant crashing issues",
                "Keeps crashing on startup",
                "Crashes every time I use it"
            ])
        ]
        
        performance_reviews = [
            Review(
                id=f"perf_{i}",
                app_id="test_app",
                platform=Platform.GOOGLE_PLAY,
                rating=2,
                text=text,
                review_date=base_date - timedelta(days=i + 10),
                locale="en",
                processed=False,
                created_at=base_date
            )
            for i, text in enumerate([
                "Very slow performance",
                "App is too laggy",
                "Takes forever to load",
                "Terrible performance issues"
            ])
        ]
        
        all_reviews = crash_reviews + performance_reviews
        
        # Cluster the reviews
        clusters = nlp_processor.cluster_complaints(all_reviews, min_cluster_size=2)
        
        # Should create meaningful clusters
        assert len(clusters) >= 1
        
        # Check if clusters capture the main themes
        cluster_names = [cluster.name.lower() for cluster in clusters]
        cluster_keywords = []
        for cluster in clusters:
            cluster_keywords.extend([kw.lower() for kw in cluster.keywords])
        
        # Should identify crash and performance related issues
        has_crash_cluster = any('crash' in name for name in cluster_names) or \
                           any('crash' in kw for kw in cluster_keywords)
        has_performance_cluster = any(word in ' '.join(cluster_names + cluster_keywords) 
                                    for word in ['slow', 'performance', 'lag'])
        
        # At least one of the main themes should be identified
        assert has_crash_cluster or has_performance_cluster
    
    def test_ranking_algorithm_accuracy(self, nlp_processor):
        """Test that ranking algorithm properly weights frequency and recency."""
        base_date = datetime.now()
        
        # Create reviews with different recency patterns
        old_frequent_reviews = [
            Review(
                id=f"old_{i}",
                app_id="test_app",
                platform=Platform.GOOGLE_PLAY,
                rating=1,
                text=f"Old frequent issue number {i}",
                review_date=base_date - timedelta(days=120 + i),  # Old reviews
                locale="en",
                processed=False,
                created_at=base_date
            )
            for i in range(10)  # Many old reviews
        ]
        
        recent_few_reviews = [
            Review(
                id=f"recent_{i}",
                app_id="test_app",
                platform=Platform.GOOGLE_PLAY,
                rating=1,
                text=f"Recent urgent issue number {i}",
                review_date=base_date - timedelta(days=i),  # Recent reviews
                locale="en",
                processed=False,
                created_at=base_date
            )
            for i in range(3)  # Few recent reviews
        ]
        
        all_reviews = old_frequent_reviews + recent_few_reviews
        
        # Cluster and check ranking
        clusters = nlp_processor.cluster_complaints(all_reviews, min_cluster_size=2)
        
        if len(clusters) >= 2:
            # Find clusters that might correspond to our test data
            for cluster in clusters:
                # Clusters should have reasonable recency scores
                assert 0 <= cluster.recency_score <= 100
                
                # Recent clusters should have higher recency scores
                if any('recent' in sample for sample in cluster.sample_reviews):
                    assert cluster.recency_score > 50  # Should be high for recent reviews
    
    def test_edge_cases_handling(self, nlp_processor):
        """Test handling of edge cases in clustering."""
        base_date = datetime.now()
        
        # Test with very short reviews
        short_reviews = [
            Review(
                id=f"short_{i}",
                app_id="test_app",
                platform=Platform.GOOGLE_PLAY,
                rating=1,
                text="Bad",
                review_date=base_date,
                locale="en",
                processed=False,
                created_at=base_date
            )
            for i in range(5)
        ]
        
        # Should handle gracefully
        clusters = nlp_processor.cluster_complaints(short_reviews, min_cluster_size=2)
        assert isinstance(clusters, list)  # Should not crash
        
        # Test with empty/whitespace reviews
        empty_reviews = [
            Review(
                id=f"empty_{i}",
                app_id="test_app",
                platform=Platform.GOOGLE_PLAY,
                rating=1,
                text="   " if i % 2 == 0 else ".",  # Use "." instead of empty string
                review_date=base_date,
                locale="en",
                processed=False,
                created_at=base_date
            )
            for i in range(3)
        ]
        
        # Should handle gracefully
        clusters = nlp_processor.cluster_complaints(empty_reviews, min_cluster_size=2)
        assert isinstance(clusters, list)  # Should not crash
    
    def test_performance_with_large_dataset(self, nlp_processor):
        """Test performance with a larger dataset."""
        base_date = datetime.now()
        
        # Create a larger dataset
        large_dataset = []
        complaint_templates = [
            "App crashes when {}",
            "Performance is slow during {}",
            "Battery drains fast while {}",
            "Login fails when {}",
            "Sync issues with {}"
        ]
        
        actions = ["startup", "usage", "loading", "scrolling", "background"]
        
        for i in range(50):  # Create 50 reviews
            template = complaint_templates[i % len(complaint_templates)]
            action = actions[i % len(actions)]
            
            review = Review(
                id=f"large_{i}",
                app_id="test_app",
                platform=Platform.GOOGLE_PLAY,
                rating=1 if i % 3 == 0 else 2,
                text=template.format(action),
                review_date=base_date - timedelta(days=i),
                locale="en",
                processed=False,
                created_at=base_date
            )
            large_dataset.append(review)
        
        # Should complete in reasonable time
        import time
        start_time = time.time()
        
        clusters = nlp_processor.cluster_complaints(large_dataset, min_cluster_size=3)
        insights = nlp_processor.generate_insights(large_dataset, clusters)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert processing_time < 30  # 30 seconds max for 50 reviews
        
        # Should produce meaningful results
        assert isinstance(clusters, list)
        assert isinstance(insights, dict)
        assert insights['total_reviews'] == len(large_dataset)


class TestClusteringQuality:
    """Test cases specifically for clustering quality and accuracy."""
    
    @pytest.fixture
    def nlp_processor(self):
        """Create an NLP processor instance for testing."""
        return NLPProcessor()
    
    def test_cluster_coherence(self, nlp_processor):
        """Test that clusters contain coherent, related reviews."""
        base_date = datetime.now()
        
        # Create reviews with distinct themes
        ui_reviews = [
            "Interface is confusing and hard to navigate",
            "UI design is terrible and unintuitive",
            "User interface needs major improvements",
            "Navigation is very difficult to understand"
        ]
        
        crash_reviews = [
            "App crashes immediately on startup",
            "Constant crashing makes it unusable",
            "Crashes every time I try to use it",
            "Application keeps crashing randomly"
        ]
        
        all_texts = ui_reviews + crash_reviews
        reviews = [
            Review(
                id=f"test_{i}",
                app_id="test_app",
                platform=Platform.GOOGLE_PLAY,
                rating=1,
                text=text,
                review_date=base_date - timedelta(days=i),
                locale="en",
                processed=False,
                created_at=base_date
            )
            for i, text in enumerate(all_texts)
        ]
        
        clusters = nlp_processor.cluster_complaints(reviews, min_cluster_size=2)
        
        # Should create coherent clusters
        for cluster in clusters:
            # Check if cluster keywords are related to the reviews
            keywords_text = ' '.join(cluster.keywords).lower()
            samples_text = ' '.join(cluster.sample_reviews).lower()
            
            # Keywords should appear in sample reviews
            keyword_overlap = any(keyword in samples_text for keyword in cluster.keywords)
            assert keyword_overlap, f"Keywords {cluster.keywords} not found in samples {cluster.sample_reviews}"
    
    def test_cluster_separation(self, nlp_processor):
        """Test that different complaint types are separated into different clusters."""
        base_date = datetime.now()
        
        # Create very distinct complaint types
        distinct_complaints = [
            # Payment issues
            "Cannot complete payment transaction",
            "Payment method not working properly",
            "Billing issues with subscription",
            
            # Network issues  
            "No internet connection detected",
            "Network timeout errors constantly",
            "Cannot connect to server",
            
            # Storage issues
            "Not enough storage space available",
            "Storage full error message",
            "Cannot save due to storage"
        ]
        
        reviews = [
            Review(
                id=f"distinct_{i}",
                app_id="test_app",
                platform=Platform.GOOGLE_PLAY,
                rating=1,
                text=text,
                review_date=base_date - timedelta(days=i),
                locale="en",
                processed=False,
                created_at=base_date
            )
            for i, text in enumerate(distinct_complaints)
        ]
        
        clusters = nlp_processor.cluster_complaints(reviews, min_cluster_size=2)
        
        # Should ideally create separate clusters for different issue types
        if len(clusters) > 1:
            # Check that clusters have different themes
            cluster_themes = []
            for cluster in clusters:
                theme_words = set()
                for keyword in cluster.keywords:
                    theme_words.add(keyword.lower())
                for sample in cluster.sample_reviews:
                    theme_words.update(sample.lower().split())
                cluster_themes.append(theme_words)
            
            # Clusters should have some distinct keywords
            for i, theme1 in enumerate(cluster_themes):
                for j, theme2 in enumerate(cluster_themes[i+1:], i+1):
                    # Should have some different keywords
                    overlap = len(theme1.intersection(theme2))
                    total_unique = len(theme1.union(theme2))
                    if total_unique > 0:
                        overlap_ratio = overlap / total_unique
                        # Shouldn't be completely identical
                        assert overlap_ratio < 0.9, f"Clusters {i} and {j} are too similar"