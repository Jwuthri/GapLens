"""Tests for URL parser service."""

import pytest

from app.models.schemas import AppIdentifier, Platform
from app.services.url_parser import URLParser, URLParsingError


class TestURLParser:
    """Test cases for URLParser class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = URLParser()
    
    # Google Play Store URL tests
    def test_google_play_url_with_id_parameter(self):
        """Test parsing Google Play Store URL with id parameter."""
        url = "https://play.google.com/store/apps/details?id=com.example.app"
        result = self.parser.extract_app_id(url)
        
        assert result.app_id == "com.example.app"
        assert result.platform == Platform.GOOGLE_PLAY
        assert result.app_name is None
        assert result.developer is None
    
    def test_google_play_url_with_additional_parameters(self):
        """Test Google Play URL with additional parameters."""
        url = "https://play.google.com/store/apps/details?id=com.example.app&hl=en&gl=US"
        result = self.parser.extract_app_id(url)
        
        assert result.app_id == "com.example.app"
        assert result.platform == Platform.GOOGLE_PLAY
    
    def test_google_play_url_without_https(self):
        """Test Google Play URL without https prefix."""
        url = "play.google.com/store/apps/details?id=com.example.app"
        result = self.parser.extract_app_id(url)
        
        assert result.app_id == "com.example.app"
        assert result.platform == Platform.GOOGLE_PLAY
    
    def test_google_play_url_case_insensitive(self):
        """Test Google Play URL parsing is case insensitive."""
        url = "https://PLAY.GOOGLE.COM/store/apps/details?id=com.example.app"
        result = self.parser.extract_app_id(url)
        
        assert result.app_id == "com.example.app"
        assert result.platform == Platform.GOOGLE_PLAY
    
    def test_google_play_url_with_complex_package_name(self):
        """Test Google Play URL with complex package name."""
        url = "https://play.google.com/store/apps/details?id=com.company.app_name.module"
        result = self.parser.extract_app_id(url)
        
        assert result.app_id == "com.company.app_name.module"
        assert result.platform == Platform.GOOGLE_PLAY
    
    # App Store URL tests
    def test_app_store_url_standard_format(self):
        """Test parsing standard App Store URL."""
        url = "https://apps.apple.com/us/app/example-app/id123456789"
        result = self.parser.extract_app_id(url)
        
        assert result.app_id == "123456789"
        assert result.platform == Platform.APP_STORE
    
    def test_app_store_url_itunes_domain(self):
        """Test App Store URL with itunes.apple.com domain."""
        url = "https://itunes.apple.com/us/app/example-app/id987654321"
        result = self.parser.extract_app_id(url)
        
        assert result.app_id == "987654321"
        assert result.platform == Platform.APP_STORE
    
    def test_app_store_url_without_country_code(self):
        """Test App Store URL without country code."""
        url = "https://apps.apple.com/app/id123456789"
        result = self.parser.extract_app_id(url)
        
        assert result.app_id == "123456789"
        assert result.platform == Platform.APP_STORE
    
    def test_app_store_url_with_different_country(self):
        """Test App Store URL with different country code."""
        url = "https://apps.apple.com/gb/app/example-app/id555666777"
        result = self.parser.extract_app_id(url)
        
        assert result.app_id == "555666777"
        assert result.platform == Platform.APP_STORE
    
    def test_app_store_url_10_digit_id(self):
        """Test App Store URL with 10-digit ID."""
        url = "https://apps.apple.com/us/app/example-app/id1234567890"
        result = self.parser.extract_app_id(url)
        
        assert result.app_id == "1234567890"
        assert result.platform == Platform.APP_STORE
    
    def test_app_store_url_without_https(self):
        """Test App Store URL without https prefix."""
        url = "apps.apple.com/us/app/example-app/id123456789"
        result = self.parser.extract_app_id(url)
        
        assert result.app_id == "123456789"
        assert result.platform == Platform.APP_STORE
    
    # Direct app ID tests
    def test_direct_google_play_id(self):
        """Test parsing direct Google Play app ID."""
        app_id = "com.example.app"
        result = self.parser.extract_app_id(app_id)
        
        assert result.app_id == "com.example.app"
        assert result.platform == Platform.GOOGLE_PLAY
    
    def test_direct_app_store_id(self):
        """Test parsing direct App Store app ID."""
        app_id = "123456789"
        result = self.parser.extract_app_id(app_id)
        
        assert result.app_id == "123456789"
        assert result.platform == Platform.APP_STORE
    
    def test_direct_google_play_id_with_underscores(self):
        """Test Google Play ID with underscores."""
        app_id = "com.company.app_name"
        result = self.parser.extract_app_id(app_id)
        
        assert result.app_id == "com.company.app_name"
        assert result.platform == Platform.GOOGLE_PLAY
    
    def test_direct_app_store_id_10_digits(self):
        """Test 10-digit App Store ID."""
        app_id = "1234567890"
        result = self.parser.extract_app_id(app_id)
        
        assert result.app_id == "1234567890"
        assert result.platform == Platform.APP_STORE
    
    # Edge cases and error handling
    def test_empty_string(self):
        """Test empty string input."""
        with pytest.raises(URLParsingError, match="URL or app ID cannot be empty"):
            self.parser.extract_app_id("")
    
    def test_whitespace_only(self):
        """Test whitespace-only input."""
        with pytest.raises(URLParsingError, match="URL or app ID cannot be empty"):
            self.parser.extract_app_id("   ")
    
    def test_none_input(self):
        """Test None input."""
        with pytest.raises(URLParsingError, match="URL or app ID cannot be empty"):
            self.parser.extract_app_id(None)
    
    def test_invalid_url_format(self):
        """Test invalid URL format."""
        with pytest.raises(URLParsingError, match="URL is not a valid"):
            self.parser.extract_app_id("https://invalid-store.com/app/123")
    
    def test_google_play_url_without_id_parameter(self):
        """Test Google Play URL without id parameter."""
        with pytest.raises(URLParsingError, match="URL is not a valid"):
            self.parser.extract_app_id("https://play.google.com/store/apps/details")
    
    def test_app_store_url_without_id(self):
        """Test App Store URL without app ID."""
        with pytest.raises(URLParsingError, match="URL is not a valid"):
            self.parser.extract_app_id("https://apps.apple.com/us/app/example-app")
    
    def test_invalid_google_play_id_format(self):
        """Test invalid Google Play ID format."""
        with pytest.raises(URLParsingError, match="Invalid app ID format"):
            self.parser.extract_app_id("123invalid")
    
    def test_invalid_app_store_id_format(self):
        """Test invalid App Store ID format."""
        with pytest.raises(URLParsingError, match="Invalid app ID format"):
            self.parser.extract_app_id("12345")  # Too short
    
    def test_google_play_id_starting_with_number(self):
        """Test Google Play ID starting with number (invalid)."""
        with pytest.raises(URLParsingError, match="Invalid app ID format"):
            self.parser.extract_app_id("1com.example.app")
    
    def test_google_play_id_ending_with_dot(self):
        """Test Google Play ID ending with dot (invalid)."""
        with pytest.raises(URLParsingError, match="Invalid app ID format"):
            self.parser.extract_app_id("com.example.app.")
    
    def test_app_store_id_too_long(self):
        """Test App Store ID that's too long."""
        with pytest.raises(URLParsingError, match="Invalid app ID format"):
            self.parser.extract_app_id("12345678901")  # 11 digits
    
    def test_app_store_id_with_letters(self):
        """Test App Store ID with letters (invalid)."""
        with pytest.raises(URLParsingError, match="Invalid app ID format"):
            self.parser.extract_app_id("123456abc")
    
    # URL normalization tests
    def test_url_with_trailing_slash(self):
        """Test URL with trailing slash."""
        url = "https://play.google.com/store/apps/details?id=com.example.app/"
        result = self.parser.extract_app_id(url)
        
        assert result.app_id == "com.example.app"
        assert result.platform == Platform.GOOGLE_PLAY
    
    def test_url_with_fragment(self):
        """Test URL with fragment."""
        url = "https://apps.apple.com/us/app/example-app/id123456789#details"
        result = self.parser.extract_app_id(url)
        
        assert result.app_id == "123456789"
        assert result.platform == Platform.APP_STORE
    
    def test_url_with_query_parameters_after_id(self):
        """Test URL with additional query parameters after ID."""
        url = "https://play.google.com/store/apps/details?id=com.example.app&referrer=utm_source%3Dgoogle"
        result = self.parser.extract_app_id(url)
        
        assert result.app_id == "com.example.app"
        assert result.platform == Platform.GOOGLE_PLAY
    
    # Whitespace handling
    def test_input_with_leading_whitespace(self):
        """Test input with leading whitespace."""
        result = self.parser.extract_app_id("  com.example.app")
        
        assert result.app_id == "com.example.app"
        assert result.platform == Platform.GOOGLE_PLAY
    
    def test_input_with_trailing_whitespace(self):
        """Test input with trailing whitespace."""
        result = self.parser.extract_app_id("123456789  ")
        
        assert result.app_id == "123456789"
        assert result.platform == Platform.APP_STORE
    
    def test_input_with_surrounding_whitespace(self):
        """Test input with surrounding whitespace."""
        result = self.parser.extract_app_id("  https://play.google.com/store/apps/details?id=com.example.app  ")
        
        assert result.app_id == "com.example.app"
        assert result.platform == Platform.GOOGLE_PLAY


class TestAppIdentifierValidation:
    """Test cases for AppIdentifier validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = URLParser()
    
    def test_validate_valid_google_play_identifier(self):
        """Test validation of valid Google Play identifier."""
        identifier = AppIdentifier(
            app_id="com.example.app",
            platform=Platform.GOOGLE_PLAY
        )
        
        assert self.parser.validate_app_identifier(identifier) is True
    
    def test_validate_valid_app_store_identifier(self):
        """Test validation of valid App Store identifier."""
        identifier = AppIdentifier(
            app_id="123456789",
            platform=Platform.APP_STORE
        )
        
        assert self.parser.validate_app_identifier(identifier) is True
    
    def test_validate_invalid_google_play_identifier(self):
        """Test validation of invalid Google Play identifier."""
        identifier = AppIdentifier(
            app_id="123invalid",
            platform=Platform.GOOGLE_PLAY
        )
        
        assert self.parser.validate_app_identifier(identifier) is False
    
    def test_validate_invalid_app_store_identifier(self):
        """Test validation of invalid App Store identifier."""
        identifier = AppIdentifier(
            app_id="abc123",
            platform=Platform.APP_STORE
        )
        
        assert self.parser.validate_app_identifier(identifier) is False
    
    def test_validate_wrong_platform_assignment(self):
        """Test validation with wrong platform assignment."""
        # Google Play ID assigned to App Store platform
        identifier = AppIdentifier(
            app_id="com.example.app",
            platform=Platform.APP_STORE
        )
        
        assert self.parser.validate_app_identifier(identifier) is False
        
        # App Store ID assigned to Google Play platform
        identifier = AppIdentifier(
            app_id="123456789",
            platform=Platform.GOOGLE_PLAY
        )
        
        assert self.parser.validate_app_identifier(identifier) is False


class TestURLParserEdgeCases:
    """Test edge cases and complex scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = URLParser()
    
    def test_malformed_url_with_multiple_domains(self):
        """Test malformed URL with multiple domains."""
        with pytest.raises(URLParsingError):
            self.parser.extract_app_id("https://play.google.com.fake.com/store/apps/details?id=com.example.app")
    
    def test_url_with_port_number(self):
        """Test URL with port number."""
        with pytest.raises(URLParsingError):
            self.parser.extract_app_id("https://play.google.com:8080/store/apps/details?id=com.example.app")
    
    def test_google_play_id_with_special_characters(self):
        """Test Google Play ID with invalid special characters."""
        with pytest.raises(URLParsingError):
            self.parser.extract_app_id("com.example.app@test")
    
    def test_very_long_google_play_id(self):
        """Test very long Google Play ID (should fail validation)."""
        long_id = "com." + "a" * 250 + ".app"
        with pytest.raises(Exception):  # Should fail due to length validation
            self.parser.extract_app_id(long_id)
    
    def test_long_but_valid_google_play_id(self):
        """Test long but valid Google Play ID."""
        # Create an ID that's close to but under the 255 character limit
        long_id = "com." + "a" * 240 + ".app"  # Should be around 248 characters
        result = self.parser.extract_app_id(long_id)
        
        assert result.app_id == long_id
        assert result.platform == Platform.GOOGLE_PLAY
    
    def test_minimum_valid_google_play_id(self):
        """Test minimum valid Google Play ID."""
        result = self.parser.extract_app_id("a.b")
        
        assert result.app_id == "a.b"
        assert result.platform == Platform.GOOGLE_PLAY
    
    def test_app_store_id_exactly_8_digits(self):
        """Test App Store ID with exactly 8 digits."""
        result = self.parser.extract_app_id("12345678")
        
        assert result.app_id == "12345678"
        assert result.platform == Platform.APP_STORE
    
    def test_app_store_id_exactly_10_digits(self):
        """Test App Store ID with exactly 10 digits."""
        result = self.parser.extract_app_id("1234567890")
        
        assert result.app_id == "1234567890"
        assert result.platform == Platform.APP_STORE
    
    def test_url_with_encoded_characters(self):
        """Test URL with encoded characters."""
        url = "https://play.google.com/store/apps/details?id=com.example.app&referrer=utm_source%3Dgoogle"
        result = self.parser.extract_app_id(url)
        
        assert result.app_id == "com.example.app"
        assert result.platform == Platform.GOOGLE_PLAY