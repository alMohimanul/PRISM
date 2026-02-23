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
    document_ids: Optional[List[str]] = Field(
        None, description="Optional list of document IDs to filter context (for multi-doc queries)"
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


class DebateRequest(BaseModel):
    """Request model for debate arena."""

    document_ids: List[str] = Field(
        ..., min_length=2, description="List of document IDs to debate (minimum 2)"
    )
    topic: Optional[str] = Field(None, description="Optional specific debate topic")
    rounds: int = Field(5, ge=1, le=10, description="Number of debate rounds (1-10)")
    humor_level: str = Field(
        "medium", description="Humor level: 'low', 'medium', or 'high'"
    )


class LiteratureReviewRequest(BaseModel):
    """Request model for literature review generation."""

    document_ids: List[str] = Field(
        ..., min_length=2, description="List of document IDs to review (minimum 2)"
    )
    research_topic: str = Field(
        "Research Topic", description="Topic/title for the literature review"
    )


class PaperComparisonRequest(BaseModel):
    """Request model for paper comparison."""

    document_ids: List[str] = Field(
        ..., min_length=2, max_length=4, description="List of document IDs to compare (2-4 papers)"
    )
    focus: Optional[str] = Field(
        "all", description="Focus area: 'methodology', 'datasets', 'results', or 'all'"
    )
