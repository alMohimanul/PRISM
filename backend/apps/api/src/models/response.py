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


class EvidenceSource(BaseModel):
    """Evidence source with grounding information."""

    chunk_id: str = Field(..., description="Chunk identifier")
    document_id: str = Field(..., description="Source document ID")
    text: str = Field(..., description="Full chunk text")
    score: float = Field(..., description="Relevance score")
    page: Optional[int] = Field(None, description="Page number in document")


class UnsupportedSpan(BaseModel):
    """Unsupported text span in answer."""

    text: str = Field(..., description="Unsupported text")
    reason: str = Field(..., description="Reason why it's unsupported")


class ChatResponse(BaseModel):
    """Chat response from agent."""

    session_id: str = Field(..., description="Session identifier")
    message: str = Field(..., description="Agent response")
    agent_type: str = Field(..., description="Agent that handled the request")
    sources: Optional[List[EvidenceSource]] = Field(
        None, description="Evidence sources with grounding"
    )
    confidence: float = Field(0.0, description="Answer confidence score (0-1)")
    unsupported_spans: List[UnsupportedSpan] = Field(
        default_factory=list, description="Text spans not supported by evidence"
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


class DebateTeam(BaseModel):
    """Team information in debate."""

    name: str = Field(..., description="Team name")
    documents: List[str] = Field(..., description="Document IDs in this team")
    score: float = Field(..., description="Team score")


class DebateArgument(BaseModel):
    """Single argument in debate round."""

    argument: str = Field(..., description="The argument text")
    citations: List[Dict[str, Any]] = Field(..., description="Citation sources")
    verified: bool = Field(..., description="Whether citations are verified")
    tone: str = Field(..., description="Tone of the argument")


class DebateRound(BaseModel):
    """Single round of debate."""

    round: int = Field(..., description="Round number")
    topic: str = Field(..., description="Topic of this round")
    team_a: DebateArgument = Field(..., description="Team A's argument")
    team_b: DebateArgument = Field(..., description="Team B's argument")
    moderator_comment: str = Field(..., description="Moderator's comment")
    winner: Optional[str] = Field(None, description="Round winner: 'team_a', 'team_b', or 'tie'")
    scores: Dict[str, float] = Field(..., description="Current scores after round")


class DebateResponse(BaseModel):
    """Complete debate response."""

    team_a: DebateTeam = Field(..., description="Team A information")
    team_b: DebateTeam = Field(..., description="Team B information")
    rounds: List[DebateRound] = Field(..., description="All debate rounds")
    final_verdict: str = Field(..., description="Final verdict and winner")
    error: Optional[str] = Field(None, description="Error message if any")


class PaperMetadata(BaseModel):
    """Paper metadata in literature review."""

    document_id: str = Field(..., description="Document ID")
    title: str = Field(..., description="Paper title")
    year: int = Field(..., description="Publication year")
    key_contribution: str = Field(..., description="Main contribution")
    authors: str = Field(..., description="Authors")


class EvolutionSection(BaseModel):
    """Evolution section in literature review."""

    era: str = Field(..., description="Era name/range")
    content: str = Field(..., description="Section content")


class ReviewSections(BaseModel):
    """Individual sections of literature review."""

    problem: str = Field(..., description="Problem statement")
    evolution: List[EvolutionSection] = Field(..., description="Evolution sections")
    sota: str = Field(..., description="State-of-the-art section")
    gaps: List[str] = Field(..., description="Research gaps")
    conclusion: str = Field(..., description="Conclusion")


class LiteratureReviewResponse(BaseModel):
    """Literature review response."""

    full_review: str = Field(..., description="Complete literature review in Markdown")
    papers: List[PaperMetadata] = Field(..., description="Papers reviewed")
    sections: ReviewSections = Field(..., description="Individual sections")
    error: Optional[str] = Field(None, description="Error message if any")


class PaperContext(BaseModel):
    """Paper context in comparison."""

    document_id: str = Field(..., description="Document ID")
    title: str = Field(..., description="Paper title")
    context: str = Field(..., description="Retrieved context")


class ComparisonInsights(BaseModel):
    """Insights from paper comparison."""

    best_performers: Dict[str, str] = Field(..., description="Best paper per dimension")
    common_patterns: List[str] = Field(..., description="Common methodologies/approaches")
    key_differences: List[str] = Field(..., description="Key differences between papers")


class PaperComparisonResponse(BaseModel):
    """Paper comparison response."""

    comparison_matrix: Dict[str, Dict[str, str]] = Field(
        ..., description="Comparison matrix with dimensions and paper values"
    )
    markdown_table: str = Field(..., description="Formatted markdown table")
    insights: ComparisonInsights = Field(..., description="Insights and analysis")
    paper_contexts: List[PaperContext] = Field(..., description="Paper contexts used")
    error: Optional[str] = Field(None, description="Error message if any")
