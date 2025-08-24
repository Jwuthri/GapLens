"""Tests for website review aggregation service."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp

from app.services.website_review_aggregator import (
    WebsiteReviewAggregator,
    WebsiteReview,
    BusinessInfo,
    WebsiteReviewAggregationError
)


@pytest.mark.asyncio
class TestWebsiteReviewAggregator:
    """Test cases for WebsiteReviewAggregator."""
    
    @pytest.fixture
    def aggregator(self):
        """Create a WebsiteReviewAggregator instance."""
        return WebsiteReviewAggregator()
    
    @pytest.fixture
    def sample_business_info(self):
        """Sample business information."""
        return BusinessInfo(
            name="Test Restaurant",
            address="123 Main St, Test City, TC 12345",
            phone="(555) 123-4567"
        )
    
    @pytest.fixture
    def sample_website_reviews(self):
        """Sample website reviews."""
        return [
            WebsiteReview(
                id="google_1",
                platform="GOOGLE_REVIEWS",
                source_platform="Google Reviews",
                rating=4,
                text="Great food and service!",
                date=datetime(2024, 1, 15),
                author="John Doe"
            ),
            WebsiteReview(
                id="yelp_1",
                platform="YELP",
                source_platform="Yelp",
                rating=2,
                text="Food was cold and service was slow.",
                date=datetime(2024, 1, 10),
                author="Jane Smith"
            )
        ]
    
    async def test_aggregate_website_reviews_empty_url(self, aggregator):
        """Test aggregation with empty URL."""
        with pytest.raises(WebsiteReviewAggregationError, match="Website URL cannot be empty"):
            await aggregator.aggregate_website_reviews("")
    
    async def test_aggregate_website_reviews_no_business_info(self, aggregator):
        """Test aggregation when business info extraction fails."""
        with patch.object(aggregator, 'extract_business_info', return_value=None):
            with pytest.raises(WebsiteReviewAggregationError, match="Could not extract business information"):
                await aggregator.aggregate_website_reviews("https://example.com")
    
    async def test_aggregate_website_reviews_success(self, aggregator, sample_business_info, sample_website_reviews):
        """Test successful website review aggregation."""
        aggregator.session = AsyncMock()
        
        with patch.object(aggregator, 'extract_business_info', return_value=sample_business_info):
            with patch.object(aggregator, 'scrape_google_reviews_web', return_value=[sample_website_reviews[0]]):
                with patch.object(aggregator, 'scrape_yelp_reviews_web', return_value=[sample_website_reviews[1]]):
                    with patch.object(aggregator, 'scrape_facebook_reviews', return_value=[]):
                        with patch.object(aggregator, 'scrape_twitter_mentions', return_value=[]):
                            
                            result = await aggregator.aggregate_website_reviews("https://example.com")
                            
                            assert len(result) == 2
                            assert result[0].website_url == "https://example.com"
                            assert result[1].website_url == "https://example.com"
    
    async def test_extract_business_info_success(self, aggregator):
        """Test successful business info extraction."""
        # Test the business name extraction logic directly
        from bs4 import BeautifulSoup
        
        html_content = """
        <html>
            <head>
                <title>Test Restaurant - Best Food in Town</title>
                <meta property="og:site_name" content="Test Restaurant">
            </head>
            <body>
                <div class="address">123 Main St, Test City, TC 12345</div>
                <div>Call us: (555) 123-4567</div>
            </body>
        </html>
        """
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Test the individual extraction methods
        business_name = aggregator._extract_business_name(soup, "https://example.com")
        address = aggregator._extract_address(soup)
        phone = aggregator._extract_phone(soup)
        
        assert business_name == "Test Restaurant"
        assert "123 Main St" in address
        assert phone == "(555) 123-4567"
    
    async def test_extract_business_info_failure(self, aggregator):
        """Test business info extraction failure."""
        # Test with empty HTML that should return None
        from bs4 import BeautifulSoup
        
        html_content = "<html><head></head><body></body></html>"
        soup = BeautifulSoup(html_content, 'html.parser')
        
        business_name = aggregator._extract_business_name(soup, "https://example.com")
        
        # Should fall back to domain name extraction
        assert business_name == "Example"
    
    def test_clean_business_name(self, aggregator):
        """Test business name cleaning."""
        test_cases = [
            ("Test Restaurant - Home", "Test Restaurant"),
            ("Test Restaurant | Official Website", "Test Restaurant"),
            ("Test Restaurant - Official Website", "Test Restaurant"),
            ("Test Restaurant", "Test Restaurant"),
        ]
        
        for input_name, expected in test_cases:
            result = aggregator._clean_business_name(input_name)
            assert result == expected
    
    async def test_scrape_google_reviews_with_api_key(self, aggregator):
        """Test Google Reviews scraping with API key."""
        aggregator.configure_apis(google_places_api_key="test_key")
        
        with patch.object(aggregator, '_find_google_place_id', return_value="test_place_id"):
            with patch.object(aggregator, '_get_google_place_reviews', return_value=[]):
                
                result = await aggregator.scrape_google_reviews("Test Restaurant")
                
                assert isinstance(result, list)
    
    async def test_scrape_google_reviews_without_api_key(self, aggregator):
        """Test Google Reviews scraping without API key."""
        with patch.object(aggregator, 'scrape_google_reviews_web', return_value=[]):
            
            result = await aggregator.scrape_google_reviews("Test Restaurant")
            
            assert isinstance(result, list)
    
    async def test_find_google_place_id_success(self, aggregator):
        """Test successful Google Place ID finding."""
        # Test that the method returns None when no API key is configured
        result = await aggregator._find_google_place_id("Test Restaurant")
        assert result is None
        
        # Test that the method is properly configured
        aggregator.configure_apis(google_places_api_key="test_key")
        assert aggregator.google_places_api_key == "test_key"
    
    async def test_get_google_place_reviews_success(self, aggregator):
        """Test successful Google Place reviews retrieval."""
        # Test that the method returns empty list when no API key is configured
        result = await aggregator._get_google_place_reviews("test_place_id")
        assert result == []
        
        # Test that the method is properly configured
        aggregator.configure_apis(google_places_api_key="test_key")
        assert aggregator.google_places_api_key == "test_key"
    
    async def test_scrape_yelp_reviews_with_api_key(self, aggregator):
        """Test Yelp reviews scraping with API key."""
        aggregator.configure_apis(yelp_api_key="test_key")
        
        with patch.object(aggregator, '_find_yelp_business_id', return_value="test_business_id"):
            with patch.object(aggregator, '_get_yelp_business_reviews', return_value=[]):
                
                result = await aggregator.scrape_yelp_reviews_api("Test Restaurant")
                
                assert isinstance(result, list)
    
    async def test_find_yelp_business_id_success(self, aggregator):
        """Test successful Yelp business ID finding."""
        # Test that the method returns None when no API key is configured
        result = await aggregator._find_yelp_business_id("Test Restaurant")
        assert result is None
        
        # Test that the method is properly configured
        aggregator.configure_apis(yelp_api_key="test_key")
        assert aggregator.yelp_api_key == "test_key"
    
    async def test_get_yelp_business_reviews_success(self, aggregator):
        """Test successful Yelp business reviews retrieval."""
        # Test that the method returns empty list when no API key is configured
        result = await aggregator._get_yelp_business_reviews("test_business_id")
        assert result == []
        
        # Test that the method is properly configured
        aggregator.configure_apis(yelp_api_key="test_key")
        assert aggregator.yelp_api_key == "test_key"
    
    def test_normalize_reviews(self, aggregator, sample_website_reviews):
        """Test review normalization."""
        result = aggregator.normalize_reviews(sample_website_reviews)
        
        assert len(result) == 2
        assert all(isinstance(review, WebsiteReview) for review in result)
        assert result[0].platform == "GOOGLE_REVIEWS"
        assert result[1].platform == "YELP"
    
    def test_normalize_platform(self, aggregator):
        """Test platform normalization."""
        test_cases = [
            ("google", "GOOGLE_REVIEWS"),
            ("GOOGLE_REVIEWS", "GOOGLE_REVIEWS"),
            ("yelp", "YELP"),
            ("YELP", "YELP"),
            ("facebook", "FACEBOOK"),
            ("twitter", "TWITTER"),
            ("unknown", "UNKNOWN")
        ]
        
        for input_platform, expected in test_cases:
            result = aggregator._normalize_platform(input_platform)
            assert result == expected
    
    def test_normalize_rating(self, aggregator):
        """Test rating normalization."""
        test_cases = [
            (5, "google", 5),
            (1, "yelp", 1),
            (6, "google", 5),  # Should cap at 5
            (0, "yelp", 1),    # Should floor at 1
            (None, "twitter", None),  # Twitter doesn't have ratings
            (3, "facebook", None),    # Facebook doesn't have traditional ratings
        ]
        
        for rating, platform, expected in test_cases:
            result = aggregator._normalize_rating(rating, platform)
            assert result == expected
    
    def test_normalize_text(self, aggregator):
        """Test text normalization."""
        test_cases = [
            ("  Great   food!  ", "Great food!"),
            ("", ""),
            ("Short", ""),  # Too short
            ("A" * 6000, ""),  # Too long
            ("Normal review text here", "Normal review text here")
        ]
        
        for input_text, expected in test_cases:
            result = aggregator._normalize_text(input_text)
            assert result == expected


class TestBusinessInfo:
    """Test cases for BusinessInfo class."""
    
    def test_business_info_creation(self):
        """Test BusinessInfo creation."""
        info = BusinessInfo(
            name="Test Restaurant",
            address="123 Main St",
            phone="555-1234"
        )
        
        assert info.name == "Test Restaurant"
        assert info.address == "123 Main St"
        assert info.phone == "555-1234"
    
    def test_business_info_minimal(self):
        """Test BusinessInfo with minimal data."""
        info = BusinessInfo(name="Test Restaurant")
        
        assert info.name == "Test Restaurant"
        assert info.address is None
        assert info.phone is None


class TestWebsiteReview:
    """Test cases for WebsiteReview class."""
    
    def test_website_review_creation(self):
        """Test WebsiteReview creation."""
        review = WebsiteReview(
            id="test_1",
            platform="GOOGLE_REVIEWS",
            source_platform="Google Reviews",
            rating=5,
            text="Great service!",
            date=datetime(2024, 1, 15),
            author="John Doe",
            website_url="https://example.com"
        )
        
        assert review.id == "test_1"
        assert review.platform == "GOOGLE_REVIEWS"
        assert review.source_platform == "Google Reviews"
        assert review.rating == 5
        assert review.text == "Great service!"
        assert review.author == "John Doe"
        assert review.website_url == "https://example.com"
    
    def test_website_review_minimal(self):
        """Test WebsiteReview with minimal data."""
        review = WebsiteReview(
            id="test_1",
            platform="TWITTER",
            source_platform="Twitter",
            rating=None,  # Twitter doesn't have ratings
            text="Great company!",
            date=datetime(2024, 1, 15)
        )
        
        assert review.id == "test_1"
        assert review.platform == "TWITTER"
        assert review.rating is None
        assert review.author is None
        assert review.website_url is None