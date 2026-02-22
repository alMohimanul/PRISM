"""Multi-provider LLM client with smart load balancing between Groq and NVIDIA."""

import time
import logging
from typing import Optional, List, Dict, Any
from enum import Enum

from groq import Groq
from openai import OpenAI

from .llm_cache import LLMCache

logger = logging.getLogger(__name__)


class Provider(str, Enum):
    """Available LLM providers."""
    GROQ = "groq"
    NVIDIA = "nvidia"


class MultiProviderLLMClient:
    """Smart LLM client that load balances between Groq and NVIDIA APIs.

    This client implements:
    - Round-robin load balancing between providers
    - Automatic failover on rate limits
    - Per-provider rate limiting
    - Exponential backoff retry logic
    """

    def __init__(
        self,
        groq_api_key: str,
        groq_model: str,
        nvidia_api_key: str,
        nvidia_model: str,
        nvidia_base_url: str,
        min_request_interval: float = 2.0,
        max_retries: int = 3,
        cache: Optional[LLMCache] = None,
    ):
        """Initialize multi-provider LLM client.

        Args:
            groq_api_key: Groq API key
            groq_model: Groq model name
            nvidia_api_key: NVIDIA API key
            nvidia_model: NVIDIA model name (Note: DeepSeek is slower due to reasoning mode)
            nvidia_base_url: NVIDIA API base URL
            min_request_interval: Minimum seconds between requests per provider
            max_retries: Maximum retry attempts on failure
            cache: Optional LLM cache instance
        """
        # Initialize Groq client
        self.groq_client = Groq(api_key=groq_api_key)
        self.groq_model = groq_model

        # Initialize NVIDIA client (OpenAI-compatible)
        # DeepSeek reasoning mode can be slow, increase timeout
        self.nvidia_client = OpenAI(
            base_url=nvidia_base_url,
            api_key=nvidia_api_key,
            timeout=120.0,  # 2 minutes for DeepSeek thinking mode
            max_retries=2,  # Retry on timeout
        )
        self.nvidia_model = nvidia_model

        # Rate limiting settings
        self.min_request_interval = min_request_interval
        self.max_retries = max_retries

        # Track last request time per provider
        self.last_request_time: Dict[Provider, float] = {
            Provider.GROQ: 0.0,
            Provider.NVIDIA: 0.0,
        }

        # Round-robin state
        self.current_provider = Provider.GROQ

        # Optional cache
        self.cache = cache

        logger.info(
            f"Initialized multi-provider LLM client with Groq ({groq_model}) "
            f"and NVIDIA ({nvidia_model}){' with caching enabled' if cache else ''}"
        )

    def _get_next_provider(self) -> Provider:
        """Get next provider using round-robin strategy.

        Returns:
            Next provider to use
        """
        # Switch to next provider
        if self.current_provider == Provider.GROQ:
            self.current_provider = Provider.NVIDIA
        else:
            self.current_provider = Provider.GROQ

        return self.current_provider

    def _wait_for_rate_limit(self, provider: Provider) -> None:
        """Wait if necessary to respect rate limits for a provider.

        Args:
            provider: Provider to check rate limit for
        """
        elapsed = time.time() - self.last_request_time[provider]
        if elapsed < self.min_request_interval:
            wait_time = self.min_request_interval - elapsed
            logger.debug(f"Rate limiting {provider.value}: waiting {wait_time:.2f}s")
            time.sleep(wait_time)

    def _call_groq(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Call Groq API.

        Args:
            messages: Chat messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated response text

        Raises:
            Exception: On API error
        """
        self._wait_for_rate_limit(Provider.GROQ)

        try:
            response = self.groq_client.chat.completions.create(
                model=self.groq_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            self.last_request_time[Provider.GROQ] = time.time()
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            raise

    def _call_nvidia(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Call NVIDIA API.

        Note: DeepSeek model uses reasoning mode which adds latency for better quality.

        Args:
            messages: Chat messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated response text

        Raises:
            Exception: On API error
        """
        self._wait_for_rate_limit(Provider.NVIDIA)

        try:
            # NVIDIA API with DeepSeek
            # Note: Thinking mode disabled to avoid 504 timeouts
            # DeepSeek v3.2 still provides excellent quality without explicit thinking mode
            response = self.nvidia_client.chat.completions.create(
                model=self.nvidia_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens or 8192,
            )
            self.last_request_time[Provider.NVIDIA] = time.time()
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"NVIDIA API error: {e}")
            raise

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        preferred_provider: Optional[Provider] = None,
        use_cache: bool = True,
    ) -> str:
        """Generate chat completion with automatic load balancing and failover.

        This method:
        1. Checks cache first (if enabled)
        2. Tries the preferred provider (or next in round-robin)
        3. On rate limit or error, falls back to the other provider
        4. Implements exponential backoff retry logic
        5. Respects per-provider rate limits
        6. Caches successful responses

        Args:
            messages: Chat messages in OpenAI format
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            preferred_provider: Preferred provider (optional, uses round-robin if None)
            use_cache: Whether to use caching (default True)

        Returns:
            Generated response text

        Raises:
            Exception: If all providers fail after retries
        """
        # Try cache first (skip if running in thread pool to avoid event loop issues)
        if use_cache and self.cache:
            try:
                # Determine which model we'll use for cache key
                model = self.groq_model  # Default to Groq
                if preferred_provider == Provider.NVIDIA:
                    model = self.nvidia_model

                cached_response = await self.cache.get(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                if cached_response:
                    logger.info("Returning cached response")
                    return cached_response
            except RuntimeError as e:
                # Event loop issues - skip cache for this call
                logger.warning(f"Cache get failed due to event loop issue, skipping cache: {e}")
                use_cache = False

        # Determine provider order
        if preferred_provider:
            providers = [preferred_provider]
            # Add fallback provider
            fallback = Provider.NVIDIA if preferred_provider == Provider.GROQ else Provider.GROQ
            providers.append(fallback)
        else:
            # Round-robin: try next provider first, then fallback to other
            primary = self._get_next_provider()
            fallback = Provider.NVIDIA if primary == Provider.GROQ else Provider.GROQ
            providers = [primary, fallback]

        # Try each provider with retries
        last_exception = None
        for provider in providers:
            for attempt in range(self.max_retries):
                try:
                    logger.info(
                        f"Calling {provider.value} (attempt {attempt + 1}/{self.max_retries})"
                    )

                    if provider == Provider.GROQ:
                        response = self._call_groq(messages, temperature, max_tokens)
                    else:
                        response = self._call_nvidia(messages, temperature, max_tokens)

                    # Cache successful response
                    if use_cache and self.cache:
                        try:
                            model = self.groq_model if provider == Provider.GROQ else self.nvidia_model
                            await self.cache.set(
                                messages=messages,
                                model=model,
                                temperature=temperature,
                                response=response,
                                max_tokens=max_tokens,
                            )
                        except RuntimeError as e:
                            # Event loop issues - skip caching
                            logger.warning(f"Cache set failed due to event loop issue: {e}")

                    return response

                except Exception as e:
                    last_exception = e
                    error_str = str(e).lower()

                    # Check if it's a rate limit error
                    if "429" in error_str or "rate limit" in error_str:
                        # Exponential backoff: 3s, 6s, 12s
                        backoff_time = 3.0 * (2 ** attempt)
                        logger.warning(
                            f"{provider.value} rate limit hit (attempt {attempt + 1}), "
                            f"waiting {backoff_time}s before retry"
                        )
                        time.sleep(backoff_time)
                    elif "timeout" in error_str or "504" in error_str or "gateway" in error_str:
                        # Timeout error - likely NVIDIA DeepSeek thinking mode taking too long
                        logger.warning(
                            f"{provider.value} timeout (attempt {attempt + 1}), "
                            f"will try fallback provider if available"
                        )
                        # Don't retry on timeout, go to next provider immediately
                        break
                    else:
                        # Non-rate-limit error, try next provider immediately
                        logger.warning(
                            f"{provider.value} error (attempt {attempt + 1}): {e}"
                        )
                        break

            # If we got here, provider failed - try next one
            logger.warning(f"{provider.value} failed after {self.max_retries} attempts")

        # All providers failed
        error_msg = f"All providers failed. Last error: {last_exception}"
        logger.error(error_msg)
        raise Exception(error_msg)

    def get_provider_stats(self) -> Dict[str, Any]:
        """Get statistics about provider usage.

        Returns:
            Dictionary with provider statistics
        """
        return {
            "current_provider": self.current_provider.value,
            "last_request_times": {
                provider.value: self.last_request_time[provider]
                for provider in Provider
            },
            "groq_model": self.groq_model,
            "nvidia_model": self.nvidia_model,
        }
