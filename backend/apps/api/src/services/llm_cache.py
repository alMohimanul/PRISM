"""LLM response caching service using Redis."""

import hashlib
import json
import logging
from typing import Optional, Dict, Any

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class LLMCache:
    """Redis-backed cache for LLM responses.

    This cache:
    - Reduces redundant LLM API calls
    - Improves response time for repeated queries
    - Uses content-addressable storage (hash of prompt)
    - Implements TTL-based expiration
    """

    def __init__(
        self,
        redis_url: str,
        ttl_seconds: int = 86400,  # 24 hours default
        key_prefix: str = "llm_cache:",
    ):
        """Initialize LLM cache.

        Args:
            redis_url: Redis connection URL
            ttl_seconds: Time to live for cached responses (seconds)
            key_prefix: Prefix for cache keys
        """
        self.redis_url = redis_url
        self.ttl_seconds = ttl_seconds
        self.key_prefix = key_prefix
        self.redis_client: Optional[redis.Redis] = None

        # Stats tracking
        self.hits = 0
        self.misses = 0

    async def connect(self) -> None:
        """Connect to Redis."""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            await self.redis_client.ping()
            logger.info(f"LLM cache connected to Redis at {self.redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect LLM cache to Redis: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("LLM cache disconnected from Redis")

    def _generate_cache_key(
        self,
        messages: list,
        model: str,
        temperature: float,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate cache key from request parameters.

        Args:
            messages: Chat messages
            model: Model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens

        Returns:
            Cache key (hash)
        """
        # Create deterministic representation
        cache_input = {
            "messages": messages,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # Hash the input
        cache_str = json.dumps(cache_input, sort_keys=True)
        cache_hash = hashlib.sha256(cache_str.encode()).hexdigest()[:16]

        return f"{self.key_prefix}{cache_hash}"

    async def get(
        self,
        messages: list,
        model: str,
        temperature: float,
        max_tokens: Optional[int] = None,
    ) -> Optional[str]:
        """Get cached response if available.

        Args:
            messages: Chat messages
            model: Model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens

        Returns:
            Cached response or None if not found
        """
        if not self.redis_client:
            return None

        try:
            cache_key = self._generate_cache_key(messages, model, temperature, max_tokens)
            cached_response = await self.redis_client.get(cache_key)

            if cached_response:
                self.hits += 1
                logger.debug(f"Cache HIT: {cache_key}")
                return cached_response
            else:
                self.misses += 1
                logger.debug(f"Cache MISS: {cache_key}")
                return None

        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set(
        self,
        messages: list,
        model: str,
        temperature: float,
        response: str,
        max_tokens: Optional[int] = None,
    ) -> None:
        """Cache an LLM response.

        Args:
            messages: Chat messages
            model: Model name
            temperature: Sampling temperature
            response: LLM response to cache
            max_tokens: Maximum tokens
        """
        if not self.redis_client:
            return

        try:
            cache_key = self._generate_cache_key(messages, model, temperature, max_tokens)
            await self.redis_client.setex(
                cache_key,
                self.ttl_seconds,
                response,
            )
            logger.debug(f"Cache SET: {cache_key} (TTL: {self.ttl_seconds}s)")

        except Exception as e:
            logger.error(f"Cache set error: {e}")

    async def invalidate_all(self) -> int:
        """Clear all cache entries.

        Returns:
            Number of keys deleted
        """
        if not self.redis_client:
            return 0

        try:
            # Find all keys with our prefix
            keys = []
            async for key in self.redis_client.scan_iter(f"{self.key_prefix}*"):
                keys.append(key)

            if keys:
                deleted = await self.redis_client.delete(*keys)
                logger.info(f"Cache invalidated: {deleted} keys deleted")
                return deleted
            return 0

        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
            return 0

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        if not self.redis_client:
            return {
                "status": "disconnected",
                "hits": 0,
                "misses": 0,
                "hit_rate": 0.0,
                "total_keys": 0,
            }

        try:
            # Count keys with our prefix
            total_keys = 0
            async for _ in self.redis_client.scan_iter(f"{self.key_prefix}*"):
                total_keys += 1

            total_requests = self.hits + self.misses
            hit_rate = self.hits / total_requests if total_requests > 0 else 0.0

            return {
                "status": "connected",
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": hit_rate,
                "total_keys": total_keys,
                "ttl_seconds": self.ttl_seconds,
            }

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {
                "status": "error",
                "error": str(e),
            }
