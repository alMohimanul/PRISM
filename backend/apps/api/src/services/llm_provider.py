"""Multi-provider LLM client with smart load balancing between Gemini and Groq."""

import time
import logging
import re
from typing import Optional, List, Dict, Any, Union
from enum import Enum

from groq import Groq
import google.generativeai as genai

from .llm_cache import LLMCache

logger = logging.getLogger(__name__)


class Provider(str, Enum):
    """Available LLM providers."""
    GEMINI = "gemini"
    GROQ = "groq"


class MultiProviderLLMClient:
    """Smart LLM client that load balances between Gemini and Groq APIs.

    This client implements:
    - Gemini as primary, Groq as fallback
    - Automatic failover on rate limits
    - Per-provider rate limiting
    - Exponential backoff retry logic
    """

    def __init__(
        self,
        groq_api_key: str,
        groq_model: str,
        gemini_api_key: str,
        gemini_model: str,
        min_request_interval: float = 1.0,
        max_retries: int = 3,
        cache: Optional[LLMCache] = None,
    ):
        """Initialize multi-provider LLM client.

        Args:
            groq_api_key: Groq API key
            groq_model: Groq model name
            gemini_api_key: Gemini API key
            gemini_model: Gemini model name (e.g., gemini-1.5-flash)
            min_request_interval: Minimum seconds between requests per provider
            max_retries: Maximum retry attempts on failure
            cache: Optional LLM cache instance
        """
        # Initialize Groq client
        self.groq_client = Groq(api_key=groq_api_key)
        self.groq_model = groq_model

        # Initialize Gemini client
        genai.configure(api_key=gemini_api_key)
        self.gemini_model = gemini_model
        self.gemini_client = genai.GenerativeModel(gemini_model)

        # Rate limiting settings
        self.min_request_interval = min_request_interval
        self.max_retries = max(1, max_retries)

        # Track last request time per provider
        self.last_request_time: Dict[Provider, float] = {
            Provider.GROQ: 0.0,
            Provider.GEMINI: 0.0,
        }
        # Provider cooldown windows (unix timestamp). If now < cooldown, skip provider.
        self.provider_cooldown_until: Dict[Provider, float] = {
            Provider.GROQ: 0.0,
            Provider.GEMINI: 0.0,
        }
        # Free-tier protection defaults: short cooldown; rely on provider retry hints.
        self.quota_exhausted_cooldown_seconds = 300.0  # 5 minutes

        # Optional cache
        self.cache = cache

        logger.info(
            f"Initialized multi-provider LLM client with Gemini ({gemini_model}) "
            f"and Groq ({groq_model}){' with caching enabled' if cache else ''}"
        )


    def _normalize_provider(self, provider: Optional[Union[Provider, str]]) -> Optional[Provider]:
        """Normalize provider input to Provider enum.

        Allows callers to pass either Provider enum values or strings.
        """
        if provider is None:
            return None

        if isinstance(provider, Provider):
            return provider

        provider_str = str(provider).strip().lower()
        if provider_str == Provider.GEMINI.value:
            return Provider.GEMINI
        if provider_str == Provider.GROQ.value:
            return Provider.GROQ

        raise ValueError(f"Unsupported provider: {provider}")

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

    @staticmethod
    def _extract_retry_delay_seconds(error_message: str) -> Optional[float]:
        """Extract provider-recommended retry delay from error text."""
        message = error_message.lower()
        delays: List[float] = []

        # Common Gemini format: "Please retry in 4.854s"
        for match in re.findall(r"retry in\s+(\d+(?:\.\d+)?)s", message):
            delays.append(float(match))

        # Structured details can include: "seconds: 8"
        for match in re.findall(r"seconds:\s*(\d+)", message):
            delays.append(float(match))

        if not delays:
            return None
        return max(delays)

    @staticmethod
    def _is_quota_exhausted_error(error_message: str) -> bool:
        """Detect hard quota exhaustion where retries are wasteful."""
        message = error_message.lower()
        # Be strict: only treat as hard exhaustion when daily/project quota
        # markers appear. Generic "quota exceeded" can also represent transient
        # short-window throttling and should still be retried.
        hard_quota_markers = [
            "generaterequestsperday",
            "perdayperprojectpermodel",
            "free_tier_requests",
            "per day",
            "current quota",
        ]
        return any(marker in message for marker in hard_quota_markers)

    def _set_provider_cooldown(self, provider: Provider, seconds: float, reason: str) -> None:
        """Mark provider as temporarily unavailable to conserve free-tier budget."""
        cooldown_until = time.time() + max(0.0, seconds)
        self.provider_cooldown_until[provider] = cooldown_until
        logger.warning(
            f"Cooling down {provider.value} for {seconds:.1f}s due to {reason}"
        )

    def _is_provider_available(self, provider: Provider) -> bool:
        """Return True if provider is not currently in cooldown."""
        return time.time() >= self.provider_cooldown_until[provider]

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

    def _call_gemini(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Call Gemini API.

        Args:
            messages: Chat messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated response text

        Raises:
            Exception: On API error
        """
        self._wait_for_rate_limit(Provider.GEMINI)

        try:
            # Convert OpenAI-style messages to Gemini format
            # Gemini expects a single prompt or conversation history
            gemini_messages = []
            for msg in messages:
                role = "user" if msg["role"] in ["user", "system"] else "model"
                gemini_messages.append({
                    "role": role,
                    "parts": [msg["content"]]
                })

            # Configure generation
            generation_config = genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens or 2048,
            )

            # Start chat and send message
            chat = self.gemini_client.start_chat(history=gemini_messages[:-1] if len(gemini_messages) > 1 else [])
            response = chat.send_message(
                gemini_messages[-1]["parts"][0],
                generation_config=generation_config
            )

            self.last_request_time[Provider.GEMINI] = time.time()
            return response.text
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        preferred_provider: Optional[Union[Provider, str]] = None,
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
        preferred_provider_enum = self._normalize_provider(preferred_provider)

        # Try cache first (skip if running in thread pool to avoid event loop issues)
        if use_cache and self.cache:
            try:
                # Determine which model we'll use for cache key
                model = self.gemini_model  # Default to Gemini
                if preferred_provider_enum == Provider.GROQ:
                    model = self.groq_model

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

        # Determine provider order (Gemini primary, Groq fallback)
        if preferred_provider_enum:
            providers = [preferred_provider_enum]
            # Add fallback provider
            fallback = Provider.GROQ if preferred_provider_enum == Provider.GEMINI else Provider.GEMINI
            providers.append(fallback)
        else:
            # Default: Gemini first, then Groq
            providers = [Provider.GEMINI, Provider.GROQ]

        # Skip providers that are currently cooling down.
        providers = [provider for provider in providers if self._is_provider_available(provider)]
        if not providers:
            raise Exception(
                "All providers are in cooldown due to recent quota/rate-limit errors. "
                "Please retry shortly."
            )

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
                        response = self._call_gemini(messages, temperature, max_tokens)

                    # Cache successful response
                    if use_cache and self.cache:
                        try:
                            model = self.groq_model if provider == Provider.GROQ else self.gemini_model
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
                    retry_delay = self._extract_retry_delay_seconds(error_str)

                    # Check if it's a rate limit error
                    if "429" in error_str or "rate limit" in error_str:
                        if self._is_quota_exhausted_error(error_str):
                            # Hard quota exhaustion (often daily free-tier cap):
                            # skip retries on this provider and try fallback immediately.
                            cooldown_seconds = retry_delay or self.quota_exhausted_cooldown_seconds
                            self._set_provider_cooldown(provider, cooldown_seconds, "quota exhaustion")
                            logger.warning(
                                f"{provider.value} quota exhausted, skipping retries and trying fallback provider"
                            )
                            break

                        # Exponential backoff: 3s, 6s, 12s
                        backoff_time = 3.0 * (2 ** attempt)
                        if retry_delay:
                            backoff_time = max(backoff_time, retry_delay)
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
            "last_request_times": {
                provider.value: self.last_request_time[provider]
                for provider in Provider
            },
            "gemini_model": self.gemini_model,
            "groq_model": self.groq_model,
        }
