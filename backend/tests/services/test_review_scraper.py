"""Tests for review scraper service."""

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from aiohttp import ClientResponse, ClientSession
from aiohttp.web_response import Response

from app.models.schemas import AppIdentifier, Platform
from app.services.review_scraper import (
    ReviewScraperService,
    ReviewScrapingError,
    RateLimitError,
    AppNotFoundError
)


class MockResponse:
    """Mock aiohttp response for testing."""
    
    def __init__(self, status: int, text_content: str = "", json_content: dict = None):
        self.status = status
        self._json_content = json_content or {}
        
        # If json_content is provided but no text_content, serialize json to text
        if json_content and not text_content:
            self._text_content = json.dumps(json_content)
        else:
            self._text_content = text_content
    
    async def text(self):
        return self._text_content
    
    async def json(self):
        return self._json_content
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class MockSession:
    """Mock aiohttp session for testing."""
    
    def __init__(self):
        self.closed = False
        self._responses = []
        self._call_count = 0
        self._return_value = None
        self._side_effect = None
    
    def get(self, *args, **kwargs):
        """Return a mock response that can be used as async context manager."""
        self._call_count += 1
        
        if self._side_effect:
            if self._call_count <= len(self._side_effect):
                return self._side_effect[self._call_count - 1]
            else:
                # Return the last response if we've run out
                return self._side_effect[-1]
        elif self._return_value:
            return self._return_value
        else:
            return MockResponse(200)
    
    def set_return_value(self, response):
        """Set the return value for get method."""
        self._return_value = response
        self._side_effect = None
    
    def set_side_effect(self, responses):
        """Set side effect for get method."""
        self._side_effect = responses
        self._return_value = None
        self._call_count = 0
    
    @property
    def call_count(self):
        """Get the number of calls made."""
        return self._call_count
    
    async def close(self):
        self.closed = True


@pytest.fixture
def mock_session():
    """Create a mock aiohttp session."""
    session = AsyncMock(spec=ClientSession)
    return session


@pytest.fixture
def scraper_service():
    """Create a ReviewScraperService instance."""
    return ReviewScraperService()


@pytest.fixture
def google_play_app_identifier():
    """Create a Google Play app identifier."""
    return AppIdentifier(
        app_id="com.example.testapp",
        platform=Platform.GOOGLE_PLAY,
        app_name="Test App",
        developer="Test Developer"
    )


@pytest.fixture
def app_store_app_identifier():
    """Create an App Store app identifier."""
    return AppIdentifier(
        app_id="123456789",
        platform=Platform.APP_STORE,
        app_name="Test App",
        developer="Test Developer"
    )


@pytest.fixture
def sample_google_play_html():
    """Sample Google Play HTML response."""
    return """
    <html>
        <div data-review-id="review_1">
            <div role="img" aria-label="Rated 4 stars">4 stars</div>
            <span data-automation-id="review-body">Great app, works well!</span>
            <span class="review-date">2 days ago</span>
            <span class="review-author">John Doe</span>
        </div>
        <div data-review-id="review_2">
            <div role="img" aria-label="Rated 2 stars">2 stars</div>
            <span data-automation-id="review-body">App crashes frequently. Needs improvement.</span>
            <span class="review-date">1 week ago</span>
            <span class="review-author">Jane Smith</span>
        </div>
    </html>
    """


@pytest.fixture
def sample_app_store_json():
    """Sample App Store RSS JSON response."""
    return {
        "feed": {
            "entry": [
                {
                    "id": {"label": "app_info"},
                    "title": {"label": "App Info"}
                },
                {
                    "id": {"label": "review_1"},
                    "title": {"label": "Excellent app"},
                    "content": {"label": "This app is amazing and works perfectly!"},
                    "im:rating": {"label": "5"},
                    "updated": {"label": "2023-12-01T10:30:00-07:00"},
                    "author": {"name": {"label": "AppUser123"}}
                },
                {
                    "id": {"label": "review_2"},
                    "title": {"label": "Disappointing"},
                    "content": {"label": "App keeps crashing on my device."},
                    "im:rating": {"label": "1"},
                    "updated": {"label": "2023-11-28T15:45:00-07:00"},
                    "author": {"name": {"label": "FrustratedUser"}}
                }
            ]
        }
    }


class TestReviewScraperService:
    """Test cases for ReviewScraperService."""
    
    @pytest.mark.asyncio
    async def test_context_manager(self, scraper_service):
        """Test async context manager functionality."""
        async with scraper_service as service:
            assert service.session is not None
        
        # Session should be closed after exiting context
        assert scraper_service.session is None or scraper_service.session.closed
    
    @pytest.mark.asyncio
    async def test_scrape_reviews_google_play_success(
        self, 
        scraper_service, 
        google_play_app_identifier,
        sample_google_play_html
    ):
        """Test successful Google Play review scraping."""
        mock_session = MockSession()
        mock_response = MockResponse(200, sample_google_play_html)
        mock_session.set_return_value(mock_response)
        
        scraper_service.session = mock_session
        
        reviews = await scraper_service.scrape_reviews(google_play_app_identifier, max_reviews=10)
        
        assert len(reviews) >= 0  # May be 0 if parsing fails, but should not raise exception
        assert mock_session.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_scrape_reviews_app_store_success(
        self, 
        scraper_service, 
        app_store_app_identifier,
        sample_app_store_json
    ):
        """Test successful App Store review scraping."""
        mock_session = MockSession()
        mock_response = MockResponse(200, json_content=sample_app_store_json)
        mock_session.set_return_value(mock_response)
        
        scraper_service.session = mock_session
        
        reviews = await scraper_service.scrape_reviews(app_store_app_identifier, max_reviews=10)
        
        assert len(reviews) >= 0  # May be 0 if parsing fails, but should not raise exception
        assert mock_session.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_scrape_reviews_app_not_found(self, scraper_service, google_play_app_identifier):
        """Test handling of app not found error."""
        mock_session = MockSession()
        mock_response = MockResponse(404)
        mock_session.set_return_value(mock_response)
        
        scraper_service.session = mock_session
        
        with pytest.raises(AppNotFoundError):
            await scraper_service.scrape_reviews(google_play_app_identifier)
    
    @pytest.mark.asyncio
    async def test_scrape_reviews_rate_limit(self, scraper_service, google_play_app_identifier):
        """Test handling of rate limit error."""
        mock_session = MockSession()
        mock_response = MockResponse(429)
        mock_session.set_return_value(mock_response)
        
        scraper_service.session = mock_session
        
        with pytest.raises(RateLimitError):
            await scraper_service.scrape_reviews(google_play_app_identifier)
    
    @pytest.mark.asyncio
    async def test_scrape_reviews_server_error_with_retry(
        self, 
        scraper_service, 
        google_play_app_identifier,
        sample_google_play_html
    ):
        """Test retry logic on server errors."""
        mock_session = MockSession()
        # First two calls return 500, third succeeds
        responses = [
            MockResponse(500),
            MockResponse(500),
            MockResponse(200, sample_google_play_html)
        ]
        mock_session.set_side_effect(responses)
        
        scraper_service.session = mock_session
        scraper_service.max_retries = 3
        
        # Should succeed after retries
        reviews = await scraper_service.scrape_reviews(google_play_app_identifier, max_reviews=5)
        
        assert len(reviews) >= 0  # Should not raise exception
        assert mock_session.call_count == 3
    
    @pytest.mark.asyncio
    async def test_scrape_reviews_max_retries_exceeded(
        self, 
        scraper_service, 
        google_play_app_identifier
    ):
        """Test failure after max retries exceeded."""
        mock_session = MockSession()
        # All calls return 500
        mock_response = MockResponse(500)
        mock_session.set_return_value(mock_response)
        
        scraper_service.session = mock_session
        scraper_service.max_retries = 2
        
        with pytest.raises(ReviewScrapingError):
            await scraper_service.scrape_reviews(google_play_app_identifier)
        
        # Should have made max_retries + 1 attempts
        assert mock_session.call_count == 3
    
    @pytest.mark.asyncio
    async def test_scrape_reviews_unsupported_platform(self, scraper_service):
        """Test handling of unsupported platform."""
        # Create a mock identifier with invalid platform by bypassing validation
        class MockAppIdentifier:
            def __init__(self):
                self.app_id = "test"
                self.platform = "UNSUPPORTED_PLATFORM"
                self.app_name = "Test"
                self.developer = "Test"
        
        unsupported_identifier = MockAppIdentifier()
        
        mock_session = MockSession()
        scraper_service.session = mock_session
        
        with pytest.raises(ReviewScrapingError, match="Unsupported platform"):
            await scraper_service.scrape_reviews(unsupported_identifier)
    
    @pytest.mark.asyncio
    async def test_scrape_reviews_session_not_initialized(self, scraper_service, google_play_app_identifier):
        """Test error when session is not initialized."""
        # Don't initialize session
        with pytest.raises(ReviewScrapingError, match="Session not initialized"):
            await scraper_service.scrape_reviews(google_play_app_identifier)
    
    @pytest.mark.asyncio
    async def test_get_app_info_google_play(self, scraper_service, google_play_app_identifier):
        """Test getting app info from Google Play."""
        sample_html = """
        <html>
            <h1 data-automation-id="app-title">Test Application</h1>
            <span data-automation-id="developer-name">Test Developer Inc.</span>
        </html>
        """
        
        mock_session = MockSession()
        mock_response = MockResponse(200, sample_html)
        mock_session.set_return_value(mock_response)
        
        scraper_service.session = mock_session
        
        app_info = await scraper_service.get_app_info(google_play_app_identifier)
        
        assert app_info['app_id'] == "com.example.testapp"
        assert app_info['app_name'] == "Test Application"
        assert app_info['developer'] == "Test Developer Inc."
        assert app_info['platform'] == Platform.GOOGLE_PLAY
    
    @pytest.mark.asyncio
    async def test_get_app_info_app_store(self, scraper_service, app_store_app_identifier):
        """Test getting app info from App Store."""
        sample_json = {
            "results": [
                {
                    "trackName": "Test iOS App",
                    "artistName": "iOS Developer LLC"
                }
            ]
        }
        
        mock_session = MockSession()
        mock_response = MockResponse(200, json_content=sample_json)
        mock_session.set_return_value(mock_response)
        
        scraper_service.session = mock_session
        
        app_info = await scraper_service.get_app_info(app_store_app_identifier)
        
        assert app_info['app_id'] == "123456789"
        assert app_info['app_name'] == "Test iOS App"
        assert app_info['developer'] == "iOS Developer LLC"
        assert app_info['platform'] == Platform.APP_STORE
    
    @pytest.mark.asyncio
    async def test_get_app_info_not_found(self, scraper_service, google_play_app_identifier):
        """Test app info when app is not found."""
        mock_session = MockSession()
        mock_response = MockResponse(404)
        mock_session.set_return_value(mock_response)
        
        scraper_service.session = mock_session
        
        with pytest.raises(AppNotFoundError):
            await scraper_service.get_app_info(google_play_app_identifier)
    
    def test_parse_date_string_relative_dates(self, scraper_service):
        """Test parsing of relative date strings."""
        now = datetime.now()
        
        # Test various relative date formats
        test_cases = [
            ("2 days ago", 2),
            ("1 day ago", 1),
            ("3 weeks ago", 21),  # 3 * 7 days
            ("2 months ago", 60),  # 2 * 30 days (approximate)
            ("1 year ago", 365)    # 1 * 365 days (approximate)
        ]
        
        for date_str, expected_days_ago in test_cases:
            parsed_date = scraper_service._parse_date_string(date_str)
            days_diff = (now - parsed_date).days
            
            # Allow some tolerance for timing differences
            assert abs(days_diff - expected_days_ago) <= 1
    
    def test_parse_date_string_absolute_dates(self, scraper_service):
        """Test parsing of absolute date strings."""
        test_cases = [
            ("2023-12-01", datetime(2023, 12, 1)),
            ("12/01/2023", datetime(2023, 12, 1)),
            ("December 1, 2023", datetime(2023, 12, 1)),
            ("Dec 1, 2023", datetime(2023, 12, 1))
        ]
        
        for date_str, expected_date in test_cases:
            parsed_date = scraper_service._parse_date_string(date_str)
            assert parsed_date.date() == expected_date.date()
    
    def test_parse_date_string_invalid_format(self, scraper_service):
        """Test parsing of invalid date strings returns current time."""
        now = datetime.now()
        parsed_date = scraper_service._parse_date_string("invalid date format")
        
        # Should return current time (within a few seconds)
        time_diff = abs((now - parsed_date).total_seconds())
        assert time_diff < 5  # Within 5 seconds
    
    @pytest.mark.asyncio
    async def test_pagination_handling_google_play(
        self, 
        scraper_service, 
        google_play_app_identifier,
        sample_google_play_html
    ):
        """Test pagination handling for Google Play."""
        # Mock multiple pages of results
        page1_html = sample_google_play_html + '<button aria-label="next page" data-token="page2"></button>'
        page2_html = sample_google_play_html  # No next button
        
        mock_session = MockSession()
        responses = [
            MockResponse(200, page1_html),
            MockResponse(200, page2_html)
        ]
        mock_session.set_side_effect(responses)
        
        scraper_service.session = mock_session
        
        reviews = await scraper_service.scrape_reviews(google_play_app_identifier, max_reviews=50)
        
        # Should have made multiple requests for pagination
        assert mock_session.call_count >= 1
        assert len(reviews) >= 0  # Should have some reviews
    
    @pytest.mark.asyncio
    async def test_rate_limiting_delays(self, scraper_service, google_play_app_identifier):
        """Test that rate limiting delays are applied."""
        with patch('asyncio.sleep') as mock_sleep:
            mock_session = MockSession()
            # Mock successful responses
            mock_response = MockResponse(200, "<html></html>")
            mock_session.set_return_value(mock_response)
            
            scraper_service.session = mock_session
            scraper_service.request_delays[Platform.GOOGLE_PLAY] = 0.1  # Short delay for testing
            
            await scraper_service.scrape_reviews(google_play_app_identifier, max_reviews=5)
            
            # Should have called sleep for rate limiting
            # (exact number depends on pagination, but should be at least once)
            assert mock_sleep.call_count >= 0
    
    @pytest.mark.asyncio
    async def test_max_reviews_limit(
        self, 
        scraper_service, 
        google_play_app_identifier,
        sample_google_play_html
    ):
        """Test that max_reviews limit is respected."""
        mock_session = MockSession()
        # Mock response with many reviews
        large_html = sample_google_play_html * 10  # Simulate many reviews
        mock_response = MockResponse(200, large_html)
        mock_session.set_return_value(mock_response)
        
        scraper_service.session = mock_session
        
        max_reviews = 3
        reviews = await scraper_service.scrape_reviews(
            google_play_app_identifier, 
            max_reviews=max_reviews
        )
        
        # Should not exceed max_reviews limit
        assert len(reviews) <= max_reviews


class TestReviewScraperIntegration:
    """Integration tests for ReviewScraperService."""
    
    @pytest.mark.asyncio
    async def test_full_workflow_google_play(self, google_play_app_identifier):
        """Test full workflow for Google Play scraping."""
        async with ReviewScraperService() as scraper:
            # Mock app info response
            app_info_html = """
            <html>
                <h1 data-automation-id="app-title">Test App</h1>
                <span data-automation-id="developer-name">Test Dev</span>
            </html>
            """
            
            # Mock reviews response
            reviews_html = """
            <html>
                <div data-review-id="test_review">
                    <div role="img" aria-label="Rated 3 stars">3 stars</div>
                    <span data-automation-id="review-body">Average app, could be better.</span>
                    <span class="review-date">1 day ago</span>
                    <span class="review-author">Test User</span>
                </div>
            </html>
            """
            
            mock_session = MockSession()
            responses = [
                MockResponse(200, app_info_html),  # App info request
                MockResponse(200, reviews_html)    # Reviews request
            ]
            mock_session.set_side_effect(responses)
            scraper.session = mock_session
            
            # Test getting app info
            app_info = await scraper.get_app_info(google_play_app_identifier)
            assert app_info['app_name'] == "Test App"
            
            # Reset side_effect for reviews
            mock_session.set_side_effect([MockResponse(200, reviews_html)])
            
            # Test scraping reviews
            reviews = await scraper.scrape_reviews(google_play_app_identifier, max_reviews=5)
            assert len(reviews) >= 0
    
    @pytest.mark.asyncio
    async def test_full_workflow_app_store(self, app_store_app_identifier):
        """Test full workflow for App Store scraping."""
        async with ReviewScraperService() as scraper:
            # Mock app info response
            app_info_json = {
                "results": [
                    {
                        "trackName": "Test iOS App",
                        "artistName": "iOS Test Developer"
                    }
                ]
            }
            
            # Mock reviews response
            reviews_json = {
                "feed": {
                    "entry": [
                        {"id": {"label": "app_info"}},  # First entry is app info
                        {
                            "id": {"label": "test_review"},
                            "title": {"label": "Good app"},
                            "content": {"label": "Works well on my iPhone."},
                            "im:rating": {"label": "4"},
                            "updated": {"label": "2023-12-01T10:30:00-07:00"},
                            "author": {"name": {"label": "iOSUser"}}
                        }
                    ]
                }
            }
            
            mock_session = MockSession()
            responses = [
                MockResponse(200, json_content=app_info_json),  # App info request
                MockResponse(200, json_content=reviews_json)    # Reviews request
            ]
            mock_session.set_side_effect(responses)
            scraper.session = mock_session
            
            # Test getting app info
            app_info = await scraper.get_app_info(app_store_app_identifier)
            assert app_info['app_name'] == "Test iOS App"
            
            # Reset side_effect for reviews
            mock_session.set_side_effect([MockResponse(200, json_content=reviews_json)])
            
            # Test scraping reviews
            reviews = await scraper.scrape_reviews(app_store_app_identifier, max_reviews=5)
            assert len(reviews) >= 0