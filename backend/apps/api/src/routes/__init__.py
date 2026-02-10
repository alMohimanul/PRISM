"""API routes for PRISM Research Assistant."""

from .chat import router as chat_router
from .documents import router as documents_router
from .sessions import router as sessions_router

__all__ = ["chat_router", "documents_router", "sessions_router"]
