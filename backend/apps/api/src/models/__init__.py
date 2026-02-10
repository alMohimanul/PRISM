"""Pydantic models for API requests and responses."""

from .request import (
    ChatRequest,
    CompareMethodologyRequest,
    CreateSessionRequest,
    UploadDocumentResponse,
)
from .response import (
    ChatResponse,
    DocumentMetadata,
    MethodologyComparison,
    SessionResponse,
)

__all__ = [
    # Request models
    "ChatRequest",
    "CompareMethodologyRequest",
    "CreateSessionRequest",
    "UploadDocumentResponse",
    # Response models
    "ChatResponse",
    "DocumentMetadata",
    "MethodologyComparison",
    "SessionResponse",
]
