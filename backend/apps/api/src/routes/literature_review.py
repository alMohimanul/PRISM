"""Literature Review endpoints for auto-generating reviews!"""

from fastapi import APIRouter, HTTPException, status

from ..agents.literature_review_generator import LiteratureReviewGenerator
from ..models.request import LiteratureReviewRequest
from ..models.response import (
    LiteratureReviewResponse,
    PaperMetadata,
    ReviewSections,
    EvolutionSection,
)

router = APIRouter(prefix="/api/literature-review", tags=["literature-review"])

# Global instance
review_generator: LiteratureReviewGenerator = None


def set_dependencies(generator: LiteratureReviewGenerator) -> None:
    """Set service dependencies."""
    global review_generator
    review_generator = generator


@router.post("/generate", response_model=LiteratureReviewResponse)
async def generate_literature_review(
    request: LiteratureReviewRequest,
) -> LiteratureReviewResponse:
    """Generate a comprehensive literature review from selected papers.

    This endpoint automatically:
    - Extracts paper metadata and chronological ordering
    - Generates problem statement
    - Describes evolution of solutions over time
    - Identifies current state-of-the-art
    - Finds research gaps
    - Writes conclusion
    - Assembles full review with citations

    Args:
        request: Review generation request

    Returns:
        Complete literature review in Markdown

    Raises:
        HTTPException: If generation fails
    """
    try:
        result = await review_generator.generate_review(
            document_ids=request.document_ids,
            research_topic=request.research_topic,
        )

        if result.get("error"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"],
            )

        # Convert to response model
        papers = [PaperMetadata(**p) for p in result["papers"]]

        evolution_sections = [
            EvolutionSection(era=s["era"], content=s["content"])
            for s in result["sections"]["evolution"]
        ]

        sections = ReviewSections(
            problem=result["sections"]["problem"],
            evolution=evolution_sections,
            sota=result["sections"]["sota"],
            gaps=result["sections"]["gaps"],
            conclusion=result["sections"]["conclusion"],
        )

        return LiteratureReviewResponse(
            full_review=result["full_review"],
            papers=papers,
            sections=sections,
            error=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating literature review: {str(e)}",
        )
