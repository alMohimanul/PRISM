"""Cache management routes."""

import logging
from typing import Dict, Any

from fastapi import APIRouter

from ..services.llm_cache import LLMCache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cache", tags=["cache"])

# Global cache instance (injected from main.py)
_cache: LLMCache = None


def set_dependencies(cache: LLMCache) -> None:
    """Set global dependencies.

    Args:
        cache: LLM cache instance
    """
    global _cache
    _cache = cache


@router.get("/stats")
async def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics.

    Returns:
        Cache statistics including hits, misses, hit rate, and total keys
    """
    if not _cache:
        return {
            "status": "not_initialized",
            "error": "Cache not initialized",
        }

    stats = await _cache.get_stats()
    return stats


@router.delete("/clear")
async def clear_cache() -> Dict[str, Any]:
    """Clear all cache entries.

    Returns:
        Number of keys deleted
    """
    if not _cache:
        return {
            "status": "error",
            "error": "Cache not initialized",
            "deleted": 0,
        }

    deleted = await _cache.invalidate_all()
    return {
        "status": "success",
        "deleted": deleted,
        "message": f"Cleared {deleted} cache entries",
    }
