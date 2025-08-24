"""Tests for NLP text processing pipeline."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from app.services.nlp_processor import NLPProcessor
from app.models.schemas import Review, Platform, ComplaintClusterBase


@pytest.fixture
def sample_reviews():
    """Create sample reviews for testing."""
    base_date = datetime.now()
    return [
        Review(
            id="1",
            app_id="com.test.app",
            platform=Platform.GOOGLE_PLAY,
            rating=1,
            text="App crashes constantly! Very frustrating 😡",
            review_date=base_date,
            locale="en",
            processed=False,
            created_at=base_date
        ),
        Review(
            id="2",
            app_id="com.test.app",
            platform=Platform.GOOGLE_PLAY,
            rating=2,
            text="Battery drain is terrible. Phone dies quickly.",
            review_date=base_date - timedelta(days=30),
            locale="en",
            processed=False,
            created_at=base_date
        ),
        Review(
            id="3",
            app_id="com.test.app",
            platform=Platform.GOOGLE_PLAY,
            rating=5,
            text="Great app! Love it!",
            review_date=base_date,
            locale="en",
            processed=False,
            created_at=base_date
        ),
        Review(
            id="4",
            app_id="com.test.app",
            platform=Platform.GOOGLE_PLAY,
            rating=1,
            text="App crashes constantly! Very frustrating",  # Duplicate without emoji
            review_date=base_date,
            locale="en",
            processed=False,
            created_at=base_date
        ),
        Review(
            id="5",
            app_id="com.test.app",
            platform=Platform.GOOGLE_PLAY,
            rating=None,  # No rating, will use sentiment
            text="This is the worst app ever. Hate it so much!",
            review_date=base_date - timedelta(days=60),
            locale="en",
            processed=False,
            created_at=base_date
        )
    ]


class TestNLPProcessor:
    """Test cases for NLPProcessor class."""
    
    @pytest.fixture
    def nlp_processor(self):
        """Create NLPProcessor instance for testing."""
        return NLPProcessor()
    
    def test_sample_fixture(self, sample_reviews):
        """Test that sample reviews fixture works."""
        assert len(sample_reviews) == 5


class TestTextCleaning:
    """Test text cleaning functionality."""
    
    @pytest.fixture
    def nlp_processor(self):
        return NLPProcessor()
    
    def test_clean_text_basic(self, nlp_processor):
        """Test basic text cleaning."""
        text = "This is a GREAT app! 😊 Love it!!!"
        cleaned = nlp_processor.clean_text(text)
        
        assert cleaned == "this is a great app love it"
        assert "😊" not in cleaned
        assert cleaned.islower()
    
    def test_clean_text_urls_and_emails(self, nlp_processor):
        """Test removal of URLs and email addresses."""
        text = "Check out https://example.com or email me at test@example.com"
        cleaned = nlp_processor.clean_text(text)
        
        assert "https://example.com" not in cleaned
        assert "test@example.com" not in cleaned
        assert "check out" in cleaned
    
    def test_clean_text_empty_input(self, nlp_processor):
        """Test cleaning empty or None input."""
        assert nlp_processor.clean_text("") == ""
        assert nlp_processor.clean_text(None) == ""
        assert nlp_processor.clean_text("   ") == ""
    
    def test_clean_text_special_characters(self, nlp_processor):
        """Test removal of special characters."""
        text = "App has bugs!!! @#$%^&*()_+ crashes often???"
        cleaned = nlp_processor.clean_text(text)
        
        # Should keep basic punctuation for sentence structure
        assert "app has bugs" in cleaned
        assert "crashes often" in cleaned
        # Special characters should be removed
        assert "@#$%^&*()" not in cleaned
    
    def test_remove_stopwords(self, nlp_processor):
        """Test stopword removal."""
        text = "this is a great app and it works well"
        filtered = nlp_processor.remove_stopwords(text)
        
        # Common stopwords should be removed
        assert "this" not in filtered
        assert "is" not in filtered
        assert "and" not in filtered
        # Content words should remain
        assert "great" in filtered
        assert "app" in filtered
        assert "works" in filtered
        assert "well" in filtered
    
    def test_normalize_text_complete_pipeline(self, nlp_processor):
        """Test complete text normalization pipeline."""
        text = "This APP is TERRIBLE!!! 😡 It crashes and has bugs! Visit https://help.com"
        normalized = nlp_processor.normalize_text(text)
        
        # Should be lowercase, no emojis, no URLs, no stopwords
        assert normalized.islower()
        assert "😡" not in normalized
        assert "https://help.com" not in normalized
        assert "terrible" in normalized
        assert "crashes" in normalized
        assert "bugs" in normalized
        # Stopwords should be removed
        assert "this" not in normalized
        assert "and" not in normalized


class TestSentimentAnalysis:
    """Test sentiment analysis functionality."""
    
    @pytest.fixture
    def nlp_processor(self):
        return NLPProcessor()
    
    def test_analyze_sentiment_positive(self, nlp_processor):
        """Test sentiment analysis for positive text."""
        text = "This app is amazing! I love it so much!"
        sentiment = nlp_processor.analyze_sentiment(text)
        
        assert sentiment > 0  # Should be positive
    
    def test_analyze_sentiment_negative(self, nlp_processor):
        """Test sentiment analysis for negative text."""
        text = "This app is terrible! I hate it! Worst app ever!"
        sentiment = nlp_processor.analyze_sentiment(text)
        
        assert sentiment < 0  # Should be negative
    
    def test_analyze_sentiment_neutral(self, nlp_processor):
        """Test sentiment analysis for neutral text."""
        text = "This is an app. It has features."
        sentiment = nlp_processor.analyze_sentiment(text)
        
        assert -0.1 <= sentiment <= 0.1  # Should be close to neutral
    
    def test_analyze_sentiment_empty_text(self, nlp_processor):
        """Test sentiment analysis for empty text."""
        assert nlp_processor.analyze_sentiment("") == 0.0
        assert nlp_processor.analyze_sentiment(None) == 0.0


class TestReviewFiltering:
    """Test review filtering functionality."""
    
    @pytest.fixture
    def nlp_processor(self):
        return NLPProcessor()
    
    def test_filter_negative_reviews_by_rating(self, nlp_processor, sample_reviews):
        """Test filtering negative reviews by rating."""
        negative_reviews = nlp_processor.filter_negative_reviews(sample_reviews)
        
        # Should include reviews with rating 1 and 2
        negative_ids = {review.id for review in negative_reviews}
        assert "1" in negative_ids  # Rating 1
        assert "2" in negative_ids  # Rating 2
        assert "3" not in negative_ids  # Rating 5 (positive)
        assert "4" in negative_ids  # Rating 1
    
    def test_filter_negative_reviews_by_sentiment(self, nlp_processor):
        """Test filtering negative reviews by sentiment when no rating."""
        reviews = [
            Review(
                id="1",
                app_id="test",
                platform=Platform.GOOGLE_PLAY,
                rating=None,
                text="This app is terrible and I hate it!",
                review_date=datetime.now(),
                locale="en",
                processed=False,
                created_at=datetime.now()
            ),
            Review(
                id="2",
                app_id="test",
                platform=Platform.GOOGLE_PLAY,
                rating=None,
                text="This app is amazing and I love it!",
                review_date=datetime.now(),
                locale="en",
                processed=False,
                created_at=datetime.now()
            )
        ]
        
        negative_reviews = nlp_processor.filter_negative_reviews(reviews)
        
        # Should include the negative sentiment review
        assert len(negative_reviews) == 1
        assert negative_reviews[0].id == "1"
    
    def test_filter_negative_reviews_empty_list(self, nlp_processor):
        """Test filtering empty review list."""
        negative_reviews = nlp_processor.filter_negative_reviews([])
        assert negative_reviews == []


class TestDuplicateRemoval:
    """Test duplicate removal functionality."""
    
    @pytest.fixture
    def nlp_processor(self):
        return NLPProcessor()
    
    def test_remove_duplicates_similar_reviews(self, nlp_processor):
        """Test removal of similar duplicate reviews."""
        reviews = [
            Review(
                id="1",
                app_id="test",
                platform=Platform.GOOGLE_PLAY,
                rating=1,
                text="App crashes constantly when I try to open it",
                review_date=datetime.now(),
                locale="en",
                processed=False,
                created_at=datetime.now()
            ),
            Review(
                id="2",
                app_id="test",
                platform=Platform.GOOGLE_PLAY,
                rating=1,
                text="App crashes constantly when I try to open it",  # Exact duplicate
                review_date=datetime.now(),
                locale="en",
                processed=False,
                created_at=datetime.now()
            ),
            Review(
                id="3",
                app_id="test",
                platform=Platform.GOOGLE_PLAY,
                rating=1,
                text="Battery drain is terrible and phone dies quickly",  # Different topic
                review_date=datetime.now(),
                locale="en",
                processed=False,
                created_at=datetime.now()
            )
        ]
        
        unique_reviews = nlp_processor.remove_duplicates(reviews, similarity_threshold=0.85)
        
        # Should keep one crash review and the battery review
        assert len(unique_reviews) == 2
        review_texts = [review.text.lower() for review in unique_reviews]
        assert any("crash" in text for text in review_texts)
        assert any("battery" in text for text in review_texts)
    
    def test_remove_duplicates_no_duplicates(self, nlp_processor):
        """Test duplicate removal when no duplicates exist."""
        reviews = [
            Review(
                id="1",
                app_id="test",
                platform=Platform.GOOGLE_PLAY,
                rating=1,
                text="App crashes",
                review_date=datetime.now(),
                locale="en",
                processed=False,
                created_at=datetime.now()
            ),
            Review(
                id="2",
                app_id="test",
                platform=Platform.GOOGLE_PLAY,
                rating=1,
                text="Battery drain",
                review_date=datetime.now(),
                locale="en",
                processed=False,
                created_at=datetime.now()
            )
        ]
        
        unique_reviews = nlp_processor.remove_duplicates(reviews)
        assert len(unique_reviews) == 2  # Should keep both
    
    def test_remove_duplicates_empty_list(self, nlp_processor):
        """Test duplicate removal with empty list."""
        unique_reviews = nlp_processor.remove_duplicates([])
        assert unique_reviews == []
    
    def test_remove_duplicates_single_review(self, nlp_processor):
        """Test duplicate removal with single review."""
        review = Review(
            id="1",
            app_id="test",
            platform=Platform.GOOGLE_PLAY,
            rating=1,
            text="App crashes",
            review_date=datetime.now(),
            locale="en",
            processed=False,
            created_at=datetime.now()
        )
        
        unique_reviews = nlp_processor.remove_duplicates([review])
        assert len(unique_reviews) == 1
        assert unique_reviews[0] == review


class TestKeywordExtraction:
    """Test keyword extraction functionality."""
    
    @pytest.fixture
    def nlp_processor(self):
        return NLPProcessor()
    
    def test_extract_keywords_basic(self, nlp_processor):
        """Test basic keyword extraction."""
        texts = [
            "App crashes constantly and freezes",
            "Crashes happen all the time",
            "Battery drain is terrible",
            "App crashes when opening"
        ]
        
        keywords = nlp_processor.extract_keywords(texts, max_keywords=5)
        
        assert len(keywords) <= 5
        assert any("crash" in keyword.lower() for keyword in keywords)
    
    def test_extract_keywords_empty_texts(self, nlp_processor):
        """Test keyword extraction with empty texts."""
        keywords = nlp_processor.extract_keywords([])
        assert keywords == []
        
        keywords = nlp_processor.extract_keywords(["", "   ", None])
        assert keywords == []
    
    def test_extract_keywords_single_text(self, nlp_processor):
        """Test keyword extraction with single text."""
        keywords = nlp_processor.extract_keywords(["App crashes frequently"])
        
        # Should return some keywords even with single text
        assert isinstance(keywords, list)


class TestComplaintClustering:
    """Test complaint clustering functionality."""
    
    @pytest.fixture
    def nlp_processor(self):
        return NLPProcessor()
    
    def test_cluster_complaints_basic(self, nlp_processor):
        """Test basic complaint clustering."""
        base_date = datetime.now()
        reviews = [
            Review(
                id="1", app_id="test", platform=Platform.GOOGLE_PLAY, rating=1,
                text="App crashes when I open it", review_date=base_date,
                locale="en", processed=False, created_at=base_date
            ),
            Review(
                id="2", app_id="test", platform=Platform.GOOGLE_PLAY, rating=1,
                text="Crashes happen all the time", review_date=base_date,
                locale="en", processed=False, created_at=base_date
            ),
            Review(
                id="3", app_id="test", platform=Platform.GOOGLE_PLAY, rating=1,
                text="Battery drains very quickly", review_date=base_date,
                locale="en", processed=False, created_at=base_date
            ),
            Review(
                id="4", app_id="test", platform=Platform.GOOGLE_PLAY, rating=1,
                text="Battery life is terrible", review_date=base_date,
                locale="en", processed=False, created_at=base_date
            ),
            Review(
                id="5", app_id="test", platform=Platform.GOOGLE_PLAY, rating=1,
                text="App keeps crashing", review_date=base_date,
                locale="en", processed=False, created_at=base_date
            )
        ]
        
        clusters = nlp_processor.cluster_complaints(reviews, min_cluster_size=2)
        
        # Should create clusters
        assert len(clusters) > 0
        
        # Check cluster properties
        for cluster in clusters:
            assert isinstance(cluster, ComplaintClusterBase)
            assert cluster.name
            assert cluster.review_count >= 2
            assert 0 <= cluster.percentage <= 100
            assert 0 <= cluster.recency_score <= 100
            assert len(cluster.sample_reviews) <= 3
    
    def test_cluster_complaints_insufficient_reviews(self, nlp_processor):
        """Test clustering with insufficient reviews."""
        review = Review(
            id="1", app_id="test", platform=Platform.GOOGLE_PLAY, rating=1,
            text="App crashes", review_date=datetime.now(),
            locale="en", processed=False, created_at=datetime.now()
        )
        
        clusters = nlp_processor.cluster_complaints([review], min_cluster_size=3)
        assert clusters == []
    
    def test_cluster_complaints_empty_reviews(self, nlp_processor):
        """Test clustering with empty review list."""
        clusters = nlp_processor.cluster_complaints([])
        assert clusters == []


class TestRecencyScoring:
    """Test recency scoring functionality."""
    
    @pytest.fixture
    def nlp_processor(self):
        return NLPProcessor()
    
    def test_calculate_recency_score_recent_reviews(self, nlp_processor):
        """Test recency score calculation for recent reviews."""
        base_date = datetime.now()
        reviews = [
            Review(
                id="1", app_id="test", platform=Platform.GOOGLE_PLAY, rating=1,
                text="Recent review", review_date=base_date,  # Recent
                locale="en", processed=False, created_at=base_date
            ),
            Review(
                id="2", app_id="test", platform=Platform.GOOGLE_PLAY, rating=1,
                text="Another recent review", review_date=base_date - timedelta(days=30),  # Recent
                locale="en", processed=False, created_at=base_date
            )
        ]
        
        recency_score = nlp_processor._calculate_recency_score(reviews)
        
        # Both reviews are recent (within 3 months)
        assert recency_score == 100.0
    
    def test_calculate_recency_score_old_reviews(self, nlp_processor):
        """Test recency score calculation for old reviews."""
        base_date = datetime.now()
        reviews = [
            Review(
                id="1", app_id="test", platform=Platform.GOOGLE_PLAY, rating=1,
                text="Old review", review_date=base_date - timedelta(days=200),  # Old
                locale="en", processed=False, created_at=base_date
            ),
            Review(
                id="2", app_id="test", platform=Platform.GOOGLE_PLAY, rating=1,
                text="Another old review", review_date=base_date - timedelta(days=300),  # Old
                locale="en", processed=False, created_at=base_date
            )
        ]
        
        recency_score = nlp_processor._calculate_recency_score(reviews)
        
        # No reviews are recent
        assert recency_score == 0.0
    
    def test_calculate_recency_score_mixed_reviews(self, nlp_processor):
        """Test recency score calculation for mixed recent/old reviews."""
        base_date = datetime.now()
        reviews = [
            Review(
                id="1", app_id="test", platform=Platform.GOOGLE_PLAY, rating=1,
                text="Recent review", review_date=base_date,  # Recent
                locale="en", processed=False, created_at=base_date
            ),
            Review(
                id="2", app_id="test", platform=Platform.GOOGLE_PLAY, rating=1,
                text="Old review", review_date=base_date - timedelta(days=200),  # Old
                locale="en", processed=False, created_at=base_date
            )
        ]
        
        recency_score = nlp_processor._calculate_recency_score(reviews)
        
        # 50% of reviews are recent
        assert recency_score == 50.0
    
    def test_calculate_recency_score_empty_reviews(self, nlp_processor):
        """Test recency score calculation for empty review list."""
        recency_score = nlp_processor._calculate_recency_score([])
        assert recency_score == 0.0


class TestCompleteProcessingPipeline:
    """Test complete processing pipeline."""
    
    @pytest.fixture
    def nlp_processor(self):
        return NLPProcessor()
    
    def test_process_reviews_complete_pipeline(self, nlp_processor, sample_reviews):
        """Test complete review processing pipeline."""
        processed_reviews = nlp_processor.process_reviews(sample_reviews)
        
        # Should filter out positive reviews and duplicates
        assert len(processed_reviews) < len(sample_reviews)
        
        # All processed reviews should be negative
        for review in processed_reviews:
            if review.rating is not None:
                assert review.rating <= 2
    
    def test_process_reviews_empty_input(self, nlp_processor):
        """Test processing empty review list."""
        processed_reviews = nlp_processor.process_reviews([])
        assert processed_reviews == []


class TestClusterRanking:
    """Test cluster ranking functionality."""
    
    @pytest.fixture
    def nlp_processor(self):
        return NLPProcessor()
    
    def test_rank_clusters_by_combined_score(self, nlp_processor):
        """Test cluster ranking by combined frequency and recency score."""
        clusters = [
            ComplaintClusterBase(
                name="Cluster A",
                description="Test cluster A", review_count=10,
                percentage=30.0, recency_score=80.0,
                sample_reviews=[], keywords=[]
            ),
            ComplaintClusterBase(
                name="Cluster B",
                description="Test cluster B", review_count=20,
                percentage=50.0, recency_score=20.0,
                sample_reviews=[], keywords=[]
            )
        ]
        
        ranked_clusters = nlp_processor.rank_clusters(clusters)
        
        # Should be sorted by combined score
        assert len(ranked_clusters) == 2
        # Cluster B should rank higher due to higher frequency despite lower recency
        # Combined score B: (50 * 0.7) + (20 * 0.3) = 35 + 6 = 41
        # Combined score A: (30 * 0.7) + (80 * 0.3) = 21 + 24 = 45
        # Actually A should rank higher due to better recency
        assert ranked_clusters[0].name == "Cluster A"
    
    def test_rank_clusters_empty_list(self, nlp_processor):
        """Test ranking empty cluster list."""
        ranked_clusters = nlp_processor.rank_clusters([])
        assert ranked_clusters == []


# Integration tests
class TestNLPProcessorIntegration:
    """Integration tests for NLP processor."""
    
    @pytest.fixture
    def nlp_processor(self):
        return NLPProcessor()
    
    def test_initialization_successful(self):
        """Test that NLP processor initializes successfully."""
        # This test verifies that the NLP processor can be initialized
        # and that NLTK data is available or downloaded automatically
        processor = NLPProcessor()
        
        # Verify that stopwords are loaded
        assert len(processor.stopwords) > 0
        assert 'the' in processor.stopwords
        assert 'and' in processor.stopwords
    
    def test_end_to_end_processing(self, nlp_processor):
        """Test end-to-end processing from raw reviews to clusters."""
        base_date = datetime.now()
        raw_reviews = [
            Review(
                id="1", app_id="test", platform=Platform.GOOGLE_PLAY, rating=1,
                text="App crashes constantly! 😡 Very frustrating experience.",
                review_date=base_date, locale="en", processed=False, created_at=base_date
            ),
            Review(
                id="2", app_id="test", platform=Platform.GOOGLE_PLAY, rating=1,
                text="Crashes happen all the time. App is unstable.",
                review_date=base_date, locale="en", processed=False, created_at=base_date
            ),
            Review(
                id="3", app_id="test", platform=Platform.GOOGLE_PLAY, rating=2,
                text="Battery drain is terrible. Phone dies quickly.",
                review_date=base_date, locale="en", processed=False, created_at=base_date
            ),
            Review(
                id="4", app_id="test", platform=Platform.GOOGLE_PLAY, rating=5,
                text="Great app! Love it!",  # Should be filtered out
                review_date=base_date, locale="en", processed=False, created_at=base_date
            ),
            Review(
                id="5", app_id="test", platform=Platform.GOOGLE_PLAY, rating=1,
                text="Battery life is awful. Drains so fast.",
                review_date=base_date, locale="en", processed=False, created_at=base_date
            )
        ]
        
        # Process reviews
        processed_reviews = nlp_processor.process_reviews(raw_reviews)
        
        # Should filter out positive review
        assert len(processed_reviews) == 4  # Excluding the 5-star review
        
        # Create clusters
        clusters = nlp_processor.cluster_complaints(processed_reviews, min_cluster_size=2)
        
        # Should create meaningful clusters
        assert len(clusters) > 0
        
        # Rank clusters
        ranked_clusters = nlp_processor.rank_clusters(clusters)
        
        # Should maintain cluster count and order
        assert len(ranked_clusters) == len(clusters)
        
        # Verify cluster properties
        for cluster in ranked_clusters:
            assert cluster.name
            assert cluster.review_count >= 2
            assert cluster.percentage > 0
            assert len(cluster.sample_reviews) > 0
            assert cluster.keywords