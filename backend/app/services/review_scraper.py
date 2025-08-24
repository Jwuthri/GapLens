"""App store review scraping service for Google Play Store and iOS App Store."""

import asyncio
import json
import random
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote_plus

import aiohttp
from bs4 import BeautifulSoup

from ..models.schemas import AppIdentifier, Platform, Review, ReviewCreate


class ReviewScrapingError(Exception):
    """Exception raised when review scraping fails."""
    pass


class RateLimitError(ReviewScrapingError):
    """Exception raised when rate limit is exceeded."""
    pass


class AppNotFoundError(ReviewScrapingError):
    """Exception raised when app is not found in store."""
    pass


class ReviewScraperService:
    """Service for scraping reviews from Google Play Store and iOS App Store."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.request_delays = {
            Platform.GOOGLE_PLAY: 1.0,  # Base delay between requests in seconds
            Platform.APP_STORE: 1.5
        }
        self.max_retries = 3
        self.backoff_factor = 2.0
        self.max_reviews_per_request = 100
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        ]
    
    async def __aenter__(self):
        """Async context manager entry."""
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': random.choice(self.user_agents)}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def scrape_reviews(
        self, 
        app_identifier: AppIdentifier, 
        max_reviews: int = 1000,
        prioritize_recent: bool = True
    ) -> List[ReviewCreate]:
        """
        Scrape reviews for an app from the appropriate store.
        
        Args:
            app_identifier: App identifier with platform and app_id
            max_reviews: Maximum number of reviews to fetch
            prioritize_recent: Whether to prioritize recent reviews
            
        Returns:
            List of ReviewCreate objects
            
        Raises:
            ReviewScrapingError: If scraping fails
            AppNotFoundError: If app is not found
            RateLimitError: If rate limit is exceeded
        """
        if not self.session:
            raise ReviewScrapingError("Session not initialized. Use async context manager.")
        
        if app_identifier.platform == Platform.GOOGLE_PLAY:
            return await self.scrape_google_play_reviews(
                app_identifier.app_id, max_reviews, prioritize_recent
            )
        elif app_identifier.platform == Platform.APP_STORE:
            return await self.scrape_app_store_reviews(
                app_identifier.app_id, max_reviews, prioritize_recent
            )
        else:
            raise ReviewScrapingError(f"Unsupported platform: {app_identifier.platform}")
    
    async def scrape_google_play_reviews(
        self, 
        app_id: str, 
        max_reviews: int = 1000,
        prioritize_recent: bool = True
    ) -> List[ReviewCreate]:
        """
        Scrape reviews from Google Play Store.
        
        Args:
            app_id: Google Play app ID (package name)
            max_reviews: Maximum number of reviews to fetch
            prioritize_recent: Whether to prioritize recent reviews
            
        Returns:
            List of ReviewCreate objects
            
        Raises:
            ReviewScrapingError: If scraping fails
            AppNotFoundError: If app is not found
        """
        reviews = []
        page_token = None
        
        try:
            while len(reviews) < max_reviews:
                batch_size = min(self.max_reviews_per_request, max_reviews - len(reviews))
                
                # Fetch a batch of reviews
                batch_reviews, next_token = await self._fetch_google_play_batch(
                    app_id, batch_size, page_token, prioritize_recent
                )
                
                if not batch_reviews:
                    break
                
                reviews.extend(batch_reviews)
                page_token = next_token
                
                if not page_token:
                    break
                
                # Rate limiting delay
                await asyncio.sleep(self.request_delays[Platform.GOOGLE_PLAY])
            
            return reviews[:max_reviews]
            
        except (AppNotFoundError, RateLimitError):
            raise
        except Exception as e:
            raise ReviewScrapingError(f"Failed to scrape Google Play reviews: {e}")
    
    async def scrape_app_store_reviews(
        self, 
        app_id: str, 
        max_reviews: int = 1000,
        prioritize_recent: bool = True
    ) -> List[ReviewCreate]:
        """
        Scrape reviews from iOS App Store.
        
        Args:
            app_id: App Store app ID (numeric)
            max_reviews: Maximum number of reviews to fetch
            prioritize_recent: Whether to prioritize recent reviews
            
        Returns:
            List of ReviewCreate objects
            
        Raises:
            ReviewScrapingError: If scraping fails
            AppNotFoundError: If app is not found
        """
        reviews = []
        page = 1
        
        try:
            while len(reviews) < max_reviews:
                batch_size = min(self.max_reviews_per_request, max_reviews - len(reviews))
                
                # Fetch a batch of reviews
                batch_reviews, has_more = await self._fetch_app_store_batch(
                    app_id, batch_size, page, prioritize_recent
                )
                
                if not batch_reviews:
                    break
                
                reviews.extend(batch_reviews)
                
                if not has_more:
                    break
                
                page += 1
                
                # Rate limiting delay
                await asyncio.sleep(self.request_delays[Platform.APP_STORE])
            
            return reviews[:max_reviews]
            
        except (AppNotFoundError, RateLimitError):
            raise
        except Exception as e:
            raise ReviewScrapingError(f"Failed to scrape App Store reviews: {e}")  
  
    async def _fetch_google_play_batch(
        self, 
        app_id: str, 
        batch_size: int, 
        page_token: Optional[str] = None,
        prioritize_recent: bool = True
    ) -> Tuple[List[ReviewCreate], Optional[str]]:
        """
        Fetch a batch of reviews from Google Play Store.
        
        Args:
            app_id: Google Play app ID
            batch_size: Number of reviews to fetch
            page_token: Token for pagination
            prioritize_recent: Whether to sort by recent first
            
        Returns:
            Tuple of (reviews, next_page_token)
        """
        # Google Play Store uses a web scraping approach since there's no official API
        # We'll use the web interface to get reviews
        
        sort_param = "newest" if prioritize_recent else "helpfulness"
        url = f"https://play.google.com/store/apps/details"
        
        params = {
            'id': app_id,
            'showAllReviews': 'true',
            'sort': sort_param
        }
        
        if page_token:
            params['pageToken'] = page_token
        
        return await self._make_request_with_retry(
            self._parse_google_play_response,
            url,
            params,
            app_id,
            batch_size
        )
    
    async def _fetch_app_store_batch(
        self, 
        app_id: str, 
        batch_size: int, 
        page: int = 1,
        prioritize_recent: bool = True
    ) -> Tuple[List[ReviewCreate], bool]:
        """
        Fetch a batch of reviews from iOS App Store.
        
        Args:
            app_id: App Store app ID
            batch_size: Number of reviews to fetch
            page: Page number for pagination
            prioritize_recent: Whether to sort by recent first
            
        Returns:
            Tuple of (reviews, has_more_pages)
        """
        # Use iTunes RSS feed for App Store reviews
        sort_param = "mostRecent" if prioritize_recent else "mostHelpful"
        
        # App Store RSS feed URL
        url = f"https://itunes.apple.com/rss/customerreviews/page={page}/id={app_id}/sortby={sort_param}/json"
        
        return await self._make_request_with_retry(
            self._parse_app_store_response,
            url,
            {},
            app_id,
            batch_size,
            page
        )
    
    async def _make_request_with_retry(
        self, 
        parser_func, 
        url: str, 
        params: Dict, 
        app_id: str, 
        batch_size: int,
        *args
    ):
        """
        Make HTTP request with exponential backoff retry logic.
        
        Args:
            parser_func: Function to parse the response
            url: Request URL
            params: Request parameters
            app_id: App ID for error context
            batch_size: Batch size for parser
            *args: Additional arguments for parser
            
        Returns:
            Parsed response from parser_func
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                # Add random jitter to user agent
                headers = {
                    'User-Agent': random.choice(self.user_agents),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                }
                
                async with self.session.get(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        content = await response.text()
                        return await parser_func(content, app_id, batch_size, *args)
                    elif response.status == 404:
                        raise AppNotFoundError(f"App not found: {app_id}")
                    elif response.status == 429:
                        raise RateLimitError("Rate limit exceeded")
                    elif response.status >= 500:
                        raise ReviewScrapingError(f"Server error: {response.status}")
                    else:
                        raise ReviewScrapingError(f"HTTP error: {response.status}")
                        
            except (AppNotFoundError, RateLimitError):
                # Don't retry these errors
                raise
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    # Exponential backoff with jitter
                    delay = (self.backoff_factor ** attempt) + random.uniform(0, 1)
                    await asyncio.sleep(delay)
                    continue
                else:
                    break
        
        # If we get here, all retries failed
        raise ReviewScrapingError(f"Failed after {self.max_retries} retries: {last_exception}")
    
    async def _parse_google_play_response(
        self, 
        html_content: str, 
        app_id: str, 
        batch_size: int
    ) -> Tuple[List[ReviewCreate], Optional[str]]:
        """
        Parse Google Play Store HTML response to extract reviews.
        
        Args:
            html_content: HTML content from Google Play
            app_id: App ID for review creation
            batch_size: Expected batch size
            
        Returns:
            Tuple of (reviews, next_page_token)
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            reviews = []
            
            # Look for review containers in Google Play's HTML structure
            # Note: Google Play's structure may change, so this is a simplified implementation
            review_containers = soup.find_all('div', {'data-review-id': True})
            
            if not review_containers:
                # Try alternative selectors
                review_containers = soup.find_all('div', class_=re.compile(r'.*review.*', re.I))
            
            for i, container in enumerate(review_containers[:batch_size]):
                try:
                    review = self._extract_google_play_review(container, app_id, i)
                    if review:
                        reviews.append(review)
                except Exception as e:
                    # Log error but continue with other reviews
                    print(f"Error parsing Google Play review {i}: {e}")
                    continue
            
            # Look for next page token (simplified implementation)
            next_token = None
            next_button = soup.find('button', {'aria-label': re.compile(r'.*next.*', re.I)})
            if next_button and next_button.get('data-token'):
                next_token = next_button['data-token']
            
            return reviews, next_token
            
        except Exception as e:
            raise ReviewScrapingError(f"Failed to parse Google Play response: {e}")
    
    async def _parse_app_store_response(
        self, 
        json_content: str, 
        app_id: str, 
        batch_size: int,
        page: int
    ) -> Tuple[List[ReviewCreate], bool]:
        """
        Parse App Store JSON response to extract reviews.
        
        Args:
            json_content: JSON content from App Store RSS
            app_id: App ID for review creation
            batch_size: Expected batch size
            page: Current page number
            
        Returns:
            Tuple of (reviews, has_more_pages)
        """
        try:
            data = json.loads(json_content)
            reviews = []
            
            # App Store RSS feed structure
            feed = data.get('feed', {})
            entries = feed.get('entry', [])
            
            # Skip the first entry as it's usually app info, not a review
            review_entries = entries[1:] if len(entries) > 1 else []
            
            for i, entry in enumerate(review_entries[:batch_size]):
                try:
                    review = self._extract_app_store_review(entry, app_id, page, i)
                    if review:
                        reviews.append(review)
                except Exception as e:
                    # Log error but continue with other reviews
                    print(f"Error parsing App Store review {i}: {e}")
                    continue
            
            # Check if there are more pages
            has_more = len(review_entries) >= batch_size
            
            return reviews, has_more
            
        except json.JSONDecodeError as e:
            raise ReviewScrapingError(f"Failed to parse App Store JSON response: {e}")
        except Exception as e:
            raise ReviewScrapingError(f"Failed to parse App Store response: {e}")
    
    def _extract_google_play_review(
        self, 
        container, 
        app_id: str, 
        index: int
    ) -> Optional[ReviewCreate]:
        """
        Extract review data from Google Play HTML container.
        
        Args:
            container: BeautifulSoup element containing review
            app_id: App ID
            index: Review index for ID generation
            
        Returns:
            ReviewCreate object or None if extraction fails
        """
        try:
            # Extract review ID
            review_id = container.get('data-review-id')
            if not review_id:
                review_id = f"gp_{app_id}_{index}_{int(datetime.now().timestamp())}"
            
            # Extract rating (look for star rating)
            rating_element = container.find('div', {'role': 'img'}) or container.find('span', class_=re.compile(r'.*star.*', re.I))
            rating = None
            if rating_element:
                rating_text = rating_element.get('aria-label', '') or rating_element.text
                rating_match = re.search(r'(\d+)', rating_text)
                if rating_match:
                    rating = int(rating_match.group(1))
            
            # Extract review text
            text_element = container.find('span', {'data-automation-id': 'review-body'}) or \
                          container.find('div', class_=re.compile(r'.*review.*text.*', re.I))
            text = text_element.text.strip() if text_element else ""
            
            # Extract date
            date_element = container.find('span', class_=re.compile(r'.*date.*', re.I))
            review_date = datetime.now()  # Default to now
            if date_element:
                try:
                    date_text = date_element.text.strip()
                    # Parse relative dates like "2 days ago" or absolute dates
                    review_date = self._parse_date_string(date_text)
                except Exception:
                    pass
            
            # Extract author
            author_element = container.find('span', class_=re.compile(r'.*author.*', re.I))
            author = author_element.text.strip() if author_element else None
            
            if not text or len(text) < 5:
                return None
            
            return ReviewCreate(
                id=review_id,
                app_id=app_id,
                platform=Platform.GOOGLE_PLAY,
                rating=rating,
                text=text,
                review_date=review_date,
                locale="en",  # Default locale
                author=author
            )
            
        except Exception as e:
            print(f"Error extracting Google Play review: {e}")
            return None
    
    def _extract_app_store_review(
        self, 
        entry: Dict, 
        app_id: str, 
        page: int, 
        index: int
    ) -> Optional[ReviewCreate]:
        """
        Extract review data from App Store RSS entry.
        
        Args:
            entry: RSS entry dictionary
            app_id: App ID
            page: Page number
            index: Review index
            
        Returns:
            ReviewCreate object or None if extraction fails
        """
        try:
            # Extract review ID
            review_id = entry.get('id', {}).get('label', f"as_{app_id}_{page}_{index}")
            
            # Extract rating
            rating = None
            im_rating = entry.get('im:rating', {})
            if im_rating and 'label' in im_rating:
                try:
                    rating = int(im_rating['label'])
                except (ValueError, TypeError):
                    pass
            
            # Extract review text
            content = entry.get('content', {})
            text = content.get('label', '') if content else ''
            
            # Extract title and combine with content if available
            title = entry.get('title', {})
            title_text = title.get('label', '') if title else ''
            
            if title_text and title_text != text:
                text = f"{title_text}\n\n{text}" if text else title_text
            
            # Extract date
            updated = entry.get('updated', {})
            date_str = updated.get('label', '') if updated else ''
            review_date = datetime.now()  # Default to now
            
            if date_str:
                try:
                    # App Store uses ISO format: 2023-12-01T10:30:00-07:00
                    review_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                except Exception:
                    try:
                        # Try parsing without timezone
                        review_date = datetime.strptime(date_str[:19], '%Y-%m-%dT%H:%M:%S')
                    except Exception:
                        pass
            
            # Extract author
            author_info = entry.get('author', {})
            author = None
            if author_info:
                author_name = author_info.get('name', {})
                if author_name and 'label' in author_name:
                    author = author_name['label']
            
            if not text or len(text) < 5:
                return None
            
            return ReviewCreate(
                id=review_id,
                app_id=app_id,
                platform=Platform.APP_STORE,
                rating=rating,
                text=text.strip(),
                review_date=review_date,
                locale="en",  # Default locale
                author=author
            )
            
        except Exception as e:
            print(f"Error extracting App Store review: {e}")
            return None
    
    def _parse_date_string(self, date_str: str) -> datetime:
        """
        Parse various date string formats.
        
        Args:
            date_str: Date string to parse
            
        Returns:
            Parsed datetime object
        """
        date_str = date_str.strip().lower()
        now = datetime.now()
        
        # Handle relative dates
        if 'ago' in date_str:
            if 'day' in date_str:
                days_match = re.search(r'(\d+)\s*day', date_str)
                if days_match:
                    days = int(days_match.group(1))
                    return now - timedelta(days=days)
            elif 'week' in date_str:
                weeks_match = re.search(r'(\d+)\s*week', date_str)
                if weeks_match:
                    weeks = int(weeks_match.group(1))
                    return now - timedelta(weeks=weeks)
            elif 'month' in date_str:
                months_match = re.search(r'(\d+)\s*month', date_str)
                if months_match:
                    months = int(months_match.group(1))
                    return now - timedelta(days=months * 30)  # Approximate
            elif 'year' in date_str:
                years_match = re.search(r'(\d+)\s*year', date_str)
                if years_match:
                    years = int(years_match.group(1))
                    return now - timedelta(days=years * 365)  # Approximate
        
        # Try common date formats
        date_formats = [
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%d/%m/%Y',
            '%B %d, %Y',
            '%b %d, %Y',
            '%Y-%m-%d %H:%M:%S',
            '%m/%d/%Y %H:%M:%S'
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # If all parsing fails, return current time
        return now
    
    async def get_app_info(self, app_identifier: AppIdentifier) -> Dict:
        """
        Get basic app information from the store.
        
        Args:
            app_identifier: App identifier with platform and app_id
            
        Returns:
            Dictionary with app information
            
        Raises:
            ReviewScrapingError: If fetching app info fails
            AppNotFoundError: If app is not found
        """
        if not self.session:
            raise ReviewScrapingError("Session not initialized. Use async context manager.")
        
        try:
            if app_identifier.platform == Platform.GOOGLE_PLAY:
                return await self._get_google_play_app_info(app_identifier.app_id)
            elif app_identifier.platform == Platform.APP_STORE:
                return await self._get_app_store_app_info(app_identifier.app_id)
            else:
                raise ReviewScrapingError(f"Unsupported platform: {app_identifier.platform}")
                
        except AppNotFoundError:
            raise
        except Exception as e:
            raise ReviewScrapingError(f"Failed to get app info: {e}")
    
    async def _get_google_play_app_info(self, app_id: str) -> Dict:
        """Get app information from Google Play Store."""
        url = "https://play.google.com/store/apps/details"
        params = {'id': app_id}
        
        try:
            headers = {'User-Agent': random.choice(self.user_agents)}
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 404:
                    raise AppNotFoundError(f"App not found: {app_id}")
                elif response.status != 200:
                    raise ReviewScrapingError(f"HTTP error: {response.status}")
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract app name
                title_element = soup.find('h1', {'data-automation-id': 'app-title'}) or \
                               soup.find('h1', class_=re.compile(r'.*title.*', re.I))
                app_name = title_element.text.strip() if title_element else None
                
                # Extract developer
                dev_element = soup.find('span', {'data-automation-id': 'developer-name'}) or \
                             soup.find('a', class_=re.compile(r'.*developer.*', re.I))
                developer = dev_element.text.strip() if dev_element else None
                
                return {
                    'app_id': app_id,
                    'app_name': app_name,
                    'developer': developer,
                    'platform': Platform.GOOGLE_PLAY
                }
                
        except AppNotFoundError:
            raise
        except Exception as e:
            raise ReviewScrapingError(f"Failed to get Google Play app info: {e}")
    
    async def _get_app_store_app_info(self, app_id: str) -> Dict:
        """Get app information from iOS App Store."""
        url = f"https://itunes.apple.com/lookup"
        params = {'id': app_id}
        
        try:
            headers = {'User-Agent': random.choice(self.user_agents)}
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    raise ReviewScrapingError(f"HTTP error: {response.status}")
                
                data = await response.json()
                results = data.get('results', [])
                
                if not results:
                    raise AppNotFoundError(f"App not found: {app_id}")
                
                app_data = results[0]
                
                return {
                    'app_id': app_id,
                    'app_name': app_data.get('trackName'),
                    'developer': app_data.get('artistName'),
                    'platform': Platform.APP_STORE
                }
                
        except AppNotFoundError:
            raise
        except Exception as e:
            raise ReviewScrapingError(f"Failed to get App Store app info: {e}")