"""Debate Arena endpoints for making papers battle!"""

from fastapi import APIRouter, HTTPException, status

from ..agents.debate_arena import DebateArenaAgent
from ..models.request import DebateRequest
from ..models.response import DebateResponse, DebateTeam, DebateRound, DebateArgument

router = APIRouter(prefix="/api/debate", tags=["debate"])

# Global instance (will be injected via dependency injection in main.py)
debate_agent: DebateArenaAgent = None


def set_dependencies(agent: DebateArenaAgent) -> None:
    """Set service dependencies.

    Args:
        agent: Debate arena agent instance
    """
    global debate_agent
    debate_agent = agent


@router.post("/start", response_model=DebateResponse)
async def start_debate(request: DebateRequest) -> DebateResponse:
    """Start a debate between research papers.

    This endpoint makes papers argue with each other in a boxing ring format!
    Perfect for comparing 2+ papers on specific topics.

    Args:
        request: Debate configuration

    Returns:
        Complete debate with all rounds and verdict

    Raises:
        HTTPException: If debate fails
    """
    try:
        # Validate humor level
        if request.humor_level not in ["low", "medium", "high"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="humor_level must be 'low', 'medium', or 'high'"
            )

        # Start the debate!
        result = await debate_agent.start_debate(
            document_ids=request.document_ids,
            topic=request.topic,
            rounds=request.rounds,
            humor_level=request.humor_level
        )

        # Check for errors
        if result.get("error"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )

        # Convert to response model
        rounds = []
        for r in result["rounds"]:
            rounds.append(
                DebateRound(
                    round=r["round"],
                    topic=r["topic"],
                    team_a=DebateArgument(**r["team_a"]),
                    team_b=DebateArgument(**r["team_b"]),
                    moderator_comment=r["moderator_comment"],
                    winner=r["winner"],
                    scores=r["scores"]
                )
            )

        return DebateResponse(
            team_a=DebateTeam(**result["team_a"]),
            team_b=DebateTeam(**result["team_b"]),
            rounds=rounds,
            final_verdict=result["final_verdict"],
            error=None
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting debate: {str(e)}"
        )
