"""Paper Comparison endpoints for comparing research papers side-by-side."""

from fastapi import APIRouter, HTTPException, status

from ..agents.paper_comparator import PaperComparator
from ..models.request import PaperComparisonRequest
from ..models.response import (
    PaperComparisonResponse,
    PaperContext,
    ComparisonInsights,
)

router = APIRouter(prefix="/api/paper-comparison", tags=["paper-comparison"])

# Global instance
paper_comparator: PaperComparator = None


def set_dependencies(comparator: PaperComparator) -> None:
    """Set service dependencies."""
    global paper_comparator
    paper_comparator = comparator


@router.post("/compare", response_model=PaperComparisonResponse)
async def compare_papers(
    request: PaperComparisonRequest,
) -> PaperComparisonResponse:
    """Compare 2-4 research papers across key dimensions.

    This endpoint automatically:
    - Retrieves relevant contexts for each paper
    - Compares papers across specified dimensions
    - Generates structured comparison matrix
    - Provides insights on best performers, patterns, and differences
    - Formats results as markdown table

    Focus areas:
    - "all": Compare across all dimensions (default)
    - "methodology": Focus on methodologies and approaches
    - "datasets": Focus on datasets and evaluation
    - "results": Focus on results and performance

    Args:
        request: Paper comparison request with document IDs and focus area

    Returns:
        Structured comparison with matrix, table, and insights

    Raises:
        HTTPException: If comparison fails or invalid input
    """
    try:
        # Validate number of papers
        if len(request.document_ids) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Need at least 2 papers to compare",
            )

        if len(request.document_ids) > 4:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 4 papers can be compared at once",
            )

        # Validate focus area
        valid_focuses = ["all", "methodology", "datasets", "results"]
        if request.focus not in valid_focuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid focus area. Must be one of: {', '.join(valid_focuses)}",
            )

        # Generate comparison
        result = await paper_comparator.compare_papers(
            document_ids=request.document_ids,
            focus=request.focus,
        )

        if result.get("error"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"],
            )

        # Convert to response model
        paper_contexts = [
            PaperContext(**pc) for pc in result["paper_contexts"]
        ]

        insights = ComparisonInsights(**result["insights"])

        return PaperComparisonResponse(
            comparison_matrix=result["comparison_matrix"],
            markdown_table=result["markdown_table"],
            insights=insights,
            paper_contexts=paper_contexts,
            error=None,
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error comparing papers: {str(e)}",
        )
