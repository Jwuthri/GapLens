"""URL parsing service for extracting app IDs from store URLs."""

import re
from typing import Optional
from urllib.parse import urlparse, parse_qs

from ..models.schemas import AppIdentifier, Platform


class URLParsingError(Exception):
    """Exception raised when URL parsing fails."""
    pass


class URLParser:
    """Service for parsing app store URLs and extracting app identifiers."""
    
    # Google Play Store URL patterns
    GOOGLE_PLAY_PATTERNS = [
        # https://play.google.com/store/apps/details?id=com.example.app
        r'play\.google\.com/store/apps/details\?.*id=([a-zA-Z0-9._]+)',
        # https://play.google.com/store/apps/details?id=com.example.app&hl=en
        r'play\.google\.com/store/apps/details.*[?&]id=([a-zA-Z0-9._]+)',
    ]
    
    # App Store URL patterns
    APP_STORE_PATTERNS = [
        # https://apps.apple.com/us/app/app-name/id123456789
        r'apps\.apple\.com/.*/app/.*/id(\d+)',
        # https://itunes.apple.com/us/app/app-name/id123456789
        r'itunes\.apple\.com/.*/app/.*/id(\d+)',
        # https://apps.apple.com/app/id123456789
        r'apps\.apple\.com/app/id(\d+)',
        # https://itunes.apple.com/app/id123456789
        r'itunes\.apple\.com/app/id(\d+)',
    ]
    
    # Direct app ID patterns
    GOOGLE_PLAY_ID_PATTERN = r'^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*){2,}$'  # Must have at least 3 parts (com.company.app)
    APP_STORE_ID_PATTERN = r'^\d{8,10}$'
    
    def extract_app_id(self, url_or_id: str) -> AppIdentifier:
        """
        Extract app identifier from URL or direct app ID.
        
        Args:
            url_or_id: App store URL or direct app ID
            
        Returns:
            AppIdentifier with platform and app_id
            
        Raises:
            URLParsingError: If URL/ID format is invalid or unsupported
        """
        if not url_or_id or not url_or_id.strip():
            raise URLParsingError("URL or app ID cannot be empty")
        
        url_or_id = url_or_id.strip()
        
        # Try to parse as URL first
        if self._is_url(url_or_id):
            return self._parse_url(url_or_id)
        
        # Try to parse as direct app ID
        return self._parse_direct_id(url_or_id)
    
    def _is_url(self, text: str) -> bool:
        """Check if text appears to be a URL."""
        if text.startswith(('http://', 'https://')):
            return True
        
        # Check if it contains URL-like patterns (domain with TLD)
        # But exclude simple package names like com.example.app
        if '.' in text:
            # If it contains app store patterns, treat as URL
            app_store_indicators = [
                'play.google.com', 'apps.apple.com', 'itunes.apple.com'
            ]
            if any(indicator in text.lower() for indicator in app_store_indicators):
                return True
            
            # If it contains common URL patterns, treat as URL
            url_indicators = [
                '.com/', '.org/', '.net/', '.edu/', '.gov/',
                'www.', 'http', 'https'
            ]
            if any(indicator in text.lower() for indicator in url_indicators):
                return True
            
            # Check if it looks like a domain name (has common TLD and no path)
            # This helps catch cases like "gorgias.com" which should be treated as website URLs
            # But exclude valid Google Play package names (which have at least 3 parts)
            common_tlds = ['.com', '.org', '.net', '.edu', '.gov', '.io', '.co', '.app', '.dev']
            if any(text.lower().endswith(tld) for tld in common_tlds) and '/' not in text:
                # Check if it's a valid Google Play package name (at least 3 parts)
                parts = text.split('.')
                if len(parts) >= 3 and all(part.replace('_', '').replace('-', '').isalnum() for part in parts):
                    # This looks like a valid package name, not a website URL
                    return False
                return True
        
        return False
    
    def _parse_url(self, url: str) -> AppIdentifier:
        """Parse app store URL to extract app ID."""
        # Normalize URL - add https if missing
        if not url.startswith(('http://', 'https://')):
            url = f'https://{url}'
        
        try:
            parsed = urlparse(url)
        except Exception as e:
            raise URLParsingError(f"Invalid URL format: {e}")
        
        # Check Google Play Store
        app_id = self._extract_google_play_id(url)
        if app_id:
            return AppIdentifier(
                app_id=app_id,
                platform=Platform.GOOGLE_PLAY
            )
        
        # Check App Store
        app_id = self._extract_app_store_id(url)
        if app_id:
            return AppIdentifier(
                app_id=app_id,
                platform=Platform.APP_STORE
            )
        
        # Check if this looks like a regular website URL
        parsed = urlparse(url)
        if parsed.netloc or any(url.lower().endswith(tld) for tld in ['.com', '.org', '.net', '.edu', '.gov', '.io', '.co', '.app', '.dev']):
            raise URLParsingError(
                f"'{url}' appears to be a website URL, not an app store URL. "
                "For website analysis, please use the website analysis feature instead. "
                "For app analysis, use Google Play Store URLs (play.google.com/store/apps/details?id=...) "
                "or App Store URLs (apps.apple.com/.../id...)"
            )
        
        raise URLParsingError(
            "URL is not a valid Google Play Store or App Store URL. "
            "Supported formats: play.google.com/store/apps/details?id=... or "
            "apps.apple.com/.../id..."
        )
    
    def _extract_google_play_id(self, url: str) -> Optional[str]:
        """Extract Google Play app ID from URL."""
        for pattern in self.GOOGLE_PLAY_PATTERNS:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                app_id = match.group(1)
                # Validate the extracted ID format
                if re.match(self.GOOGLE_PLAY_ID_PATTERN, app_id):
                    return app_id
        return None
    
    def _extract_app_store_id(self, url: str) -> Optional[str]:
        """Extract App Store app ID from URL."""
        for pattern in self.APP_STORE_PATTERNS:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                app_id = match.group(1)
                # Validate the extracted ID format
                if re.match(self.APP_STORE_ID_PATTERN, app_id):
                    return app_id
        return None
    
    def _parse_direct_id(self, app_id: str) -> AppIdentifier:
        """Parse direct app ID and determine platform."""
        # Check if it's a Google Play app ID (package name format)
        if re.match(self.GOOGLE_PLAY_ID_PATTERN, app_id):
            return AppIdentifier(
                app_id=app_id,
                platform=Platform.GOOGLE_PLAY
            )
        
        # Check if it's an App Store app ID (numeric)
        if re.match(self.APP_STORE_ID_PATTERN, app_id):
            return AppIdentifier(
                app_id=app_id,
                platform=Platform.APP_STORE
            )
        
        raise URLParsingError(
            "Invalid app ID format. Google Play IDs should be package names "
            "(e.g., com.example.app) and App Store IDs should be 8-10 digit numbers."
        )
    
    def validate_app_identifier(self, app_identifier: AppIdentifier) -> bool:
        """
        Validate an AppIdentifier object.
        
        Args:
            app_identifier: AppIdentifier to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            if app_identifier.platform == Platform.GOOGLE_PLAY:
                return bool(re.match(self.GOOGLE_PLAY_ID_PATTERN, app_identifier.app_id))
            elif app_identifier.platform == Platform.APP_STORE:
                return bool(re.match(self.APP_STORE_ID_PATTERN, app_identifier.app_id))
            return False
        except Exception:
            return False