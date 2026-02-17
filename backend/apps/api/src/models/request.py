"""Request models for API endpoints."""

from typing import List, Optional

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    """Request model for creating a new research session."""

    name: str = Field(..., description="Name of the research session")
    topic: Optional[str] = Field(None, description="Research topic for context pre-loading")
    description: Optional[str] = Field(None, description="Description of the research session")


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    session_id: str = Field(..., description="Session ID for maintaining context")
    message: str = Field(..., description="User message/question")
    agent_type: Optional[str] = Field(
        None, description="Specific agent to route to (auto-routed if not specified)"
    )


class CompareMethodologyRequest(BaseModel):
    """Request model for methodology comparison."""

    document_ids: List[str] = Field(
        ..., min_length=2, description="List of document IDs to compare"
    )
    session_id: Optional[str] = Field(None, description="Optional session ID for context")


class UploadDocumentResponse(BaseModel):
    """Response model for document upload."""

    document_id: str = Field(..., description="Unique identifier for the uploaded document")
    filename: str = Field(..., description="Original filename")
    page_count: int = Field(..., description="Number of pages in the document")
    size_bytes: int = Field(..., description="File size in bytes")
    status: str = Field(..., description="Processing status")
