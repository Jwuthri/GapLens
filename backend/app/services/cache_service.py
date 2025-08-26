"""Redis caching service for performance optimization."""

import json
import logging
import pickle
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

import redis
from redis.exceptions import ConnectionError, TimeoutError

from ..models.schemas import Analysis, ComplaintCluster, SummaryStats


class CacheService:
    """Redis-based caching service for analysis results and frequently accessed data."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/1"):
        """
        Initialize the cache service.
        
        Args:
            redis_url: Redis connection URL
        """
        self.logger = logging.getLogger(__name__)
        self.redis_client = None
        self.redis_url = redis_url
        self._connect()
    
    def _connect(self) -> None:
        """Establish Redis connection with retry logic."""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=False,  # We'll handle encoding ourselves
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            self.redis_client.ping()
            self.logger.info("Redis cache service connected successfully")
            
        except (ConnectionError, TimeoutError) as e:
            self.logger.warning(f"Redis connection failed: {e}. Cache will be disabled.")
            self.redis_client = None
        except Exception as e:
            self.logger.error(f"Unexpected error connecting to Redis: {e}")
            self.redis_client = None
    
    def is_available(self) -> bool:
        """Check if Redis cache is available."""
        if not self.redis_client:
            return False
        
        try:
            self.redis_client.ping()
            return True
        except Exception:
            return False
    
    def _serialize_data(self, data: Any) -> bytes:
        """Serialize data for Redis storage."""
        try:
            # Use pickle for complex objects, JSON for simple ones
            if isinstance(data, (dict, list, str, int, float, bool)):
                return json.dumps(data, default=str).encode('utf-8')
            else:
                return pickle.dumps(data)
        except Exception as e:
            self.logger.error(f"Failed to serialize data: {e}")
            raise
    
    def _deserialize_data(self, data: bytes) -> Any:
        """Deserialize data from Redis storage."""
        try:
            # Try JSON first, then pickle
            try:
                return json.loads(data.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return pickle.loads(data)
        except Exception as e:
            self.logger.error(f"Failed to deserialize data: {e}")
            raise
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/error
        """
        if not self.is_available():
            return None
        
        try:
            data = self.redis_client.get(key)
            if data is None:
                return None
            
            return self._deserialize_data(data)
            
        except Exception as e:
            self.logger.warning(f"Cache get failed for key '{key}': {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """
        Set value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default: 1 hour)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            return False
        
        try:
            serialized_data = self._serialize_data(value)
            result = self.redis_client.setex(key, ttl, serialized_data)
            return bool(result)
            
        except Exception as e:
            self.logger.warning(f"Cache set failed for key '{key}': {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            return False
        
        try:
            result = self.redis_client.delete(key)
            return bool(result)
            
        except Exception as e:
            self.logger.warning(f"Cache delete failed for key '{key}': {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key to check
            
        Returns:
            True if key exists, False otherwise
        """
        if not self.is_available():
            return False
        
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            self.logger.warning(f"Cache exists check failed for key '{key}': {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching a pattern.
        
        Args:
            pattern: Redis pattern (e.g., "analysis:*")
            
        Returns:
            Number of keys deleted
        """
        if not self.is_available():
            return 0
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
            
        except Exception as e:
            self.logger.warning(f"Cache clear pattern failed for '{pattern}': {e}")
            return 0
    
    # Analysis-specific caching methods
    
    def get_analysis_results(self, analysis_id: UUID) -> Optional[Dict]:
        """Get cached analysis results."""
        key = f"analysis:results:{analysis_id}"
        return self.get(key)
    
    def cache_analysis_results(self, analysis_id: UUID, results: Dict, ttl: int = 7200) -> bool:
        """
        Cache analysis results.
        
        Args:
            analysis_id: Analysis ID
            results: Analysis results dictionary
            ttl: Cache TTL in seconds (default: 2 hours)
        """
        key = f"analysis:results:{analysis_id}"
        return self.set(key, results, ttl)
    
    def get_analysis_status(self, analysis_id: UUID) -> Optional[Dict]:
        """Get cached analysis status."""
        key = f"analysis:status:{analysis_id}"
        return self.get(key)
    
    def cache_analysis_status(self, analysis_id: UUID, status: Dict, ttl: int = 300) -> bool:
        """
        Cache analysis status.
        
        Args:
            analysis_id: Analysis ID
            status: Status dictionary
            ttl: Cache TTL in seconds (default: 5 minutes)
        """
        key = f"analysis:status:{analysis_id}"
        return self.set(key, status, ttl)
    
    def get_app_reviews(self, app_id: str, platform: str) -> Optional[List]:
        """Get cached app reviews."""
        key = f"reviews:app:{platform}:{app_id}"
        return self.get(key)
    
    def cache_app_reviews(self, app_id: str, platform: str, reviews: List, ttl: int = 86400) -> bool:
        """
        Cache app reviews.
        
        Args:
            app_id: App ID
            platform: Platform name
            reviews: List of reviews
            ttl: Cache TTL in seconds (default: 24 hours)
        """
        key = f"reviews:app:{platform}:{app_id}"
        return self.set(key, reviews, ttl)
    
    def get_website_reviews(self, website_url: str) -> Optional[List]:
        """Get cached website reviews."""
        # Create a safe key from URL
        safe_url = website_url.replace('://', '_').replace('/', '_').replace('.', '_')
        key = f"reviews:website:{safe_url}"
        return self.get(key)
    
    def cache_website_reviews(self, website_url: str, reviews: List, ttl: int = 86400) -> bool:
        """
        Cache website reviews.
        
        Args:
            website_url: Website URL
            reviews: List of reviews
            ttl: Cache TTL in seconds (default: 24 hours)
        """
        safe_url = website_url.replace('://', '_').replace('/', '_').replace('.', '_')
        key = f"reviews:website:{safe_url}"
        return self.set(key, reviews, ttl)
    
    def get_nlp_embeddings(self, text_hash: str) -> Optional[Any]:
        """Get cached NLP embeddings."""
        key = f"nlp:embeddings:{text_hash}"
        return self.get(key)
    
    def cache_nlp_embeddings(self, text_hash: str, embeddings: Any, ttl: int = 604800) -> bool:
        """
        Cache NLP embeddings.
        
        Args:
            text_hash: Hash of the text content
            embeddings: Computed embeddings
            ttl: Cache TTL in seconds (default: 7 days)
        """
        key = f"nlp:embeddings:{text_hash}"
        return self.set(key, embeddings, ttl)
    
    def get_cluster_results(self, reviews_hash: str) -> Optional[List]:
        """Get cached clustering results."""
        key = f"nlp:clusters:{reviews_hash}"
        return self.get(key)
    
    def cache_cluster_results(self, reviews_hash: str, clusters: List, ttl: int = 86400) -> bool:
        """
        Cache clustering results.
        
        Args:
            reviews_hash: Hash of the review content
            clusters: Clustering results
            ttl: Cache TTL in seconds (default: 24 hours)
        """
        key = f"nlp:clusters:{reviews_hash}"
        return self.set(key, clusters, ttl)
    
    def invalidate_analysis_cache(self, analysis_id: UUID) -> None:
        """Invalidate all cache entries for an analysis."""
        patterns = [
            f"analysis:*:{analysis_id}",
            f"analysis:results:{analysis_id}",
            f"analysis:status:{analysis_id}"
        ]
        
        for pattern in patterns:
            self.clear_pattern(pattern)
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        if not self.is_available():
            return {"status": "unavailable"}
        
        try:
            info = self.redis_client.info()
            return {
                "status": "available",
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "0B"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": round(
                    info.get("keyspace_hits", 0) / 
                    max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1) * 100, 
                    2
                )
            }
        except Exception as e:
            self.logger.error(f"Failed to get cache stats: {e}")
            return {"status": "error", "error": str(e)}


# Global cache service instance
cache_service = CacheService()