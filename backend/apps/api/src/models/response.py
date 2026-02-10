"""Response models for API endpoints."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    """Document metadata response."""

    document_id: str = Field(..., description="Unique identifier")
    filename: str = Field(..., description="Original filename")
    title: Optional[str] = Field(None, description="Extracted paper title")
    authors: Optional[List[str]] = Field(None, description="List of authors")
    abstract: Optional[str] = Field(None, description="Paper abstract")
    page_count: int = Field(..., description="Number of pages")
    size_bytes: int = Field(..., description="File size in bytes")
    upload_date: datetime = Field(..., description="Upload timestamp")
    processing_status: str = Field(..., description="Processing status")


class SessionResponse(BaseModel):
    """Research session response."""

    session_id: str = Field(..., description="Unique session identifier")
    name: str = Field(..., description="Session name")
    topic: Optional[str] = Field(None, description="Research topic")
    description: Optional[str] = Field(None, description="Session description")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    document_count: int = Field(default=0, description="Number of documents in session")
    message_count: int = Field(default=0, description="Number of messages in session")


class ChatResponse(BaseModel):
    """Chat response from agent."""

    session_id: str = Field(..., description="Session identifier")
    message: str = Field(..., description="Agent response")
    agent_type: str = Field(..., description="Agent that handled the request")
    sources: Optional[List[Dict[str, Any]]] = Field(
        None, description="Source documents/citations"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class MethodologyComparison(BaseModel):
    """Methodology comparison response."""

    documents: List[str] = Field(..., description="Document IDs compared")
    comparison_table: Dict[str, Dict[str, str]] = Field(
        ..., description="Comparison table with methodology aspects"
    )
    summary: str = Field(..., description="Summary of key differences")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
