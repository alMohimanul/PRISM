"""Chat endpoints for interacting with agents."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from ..agents.literature_reviewer import LiteratureReviewerAgent
from ..models.request import ChatRequest
from ..models.response import ChatResponse
from ..services.session_manager import SessionManager

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Global instances (will be injected via dependency injection in main.py)
literature_agent: LiteratureReviewerAgent = None
session_manager: SessionManager = None


def set_dependencies(lit_agent: LiteratureReviewerAgent, sess_manager: SessionManager) -> None:
    """Set service dependencies.

    Args:
        lit_agent: Literature reviewer agent instance
        sess_manager: Session manager instance
    """
    global literature_agent, session_manager
    literature_agent = lit_agent
    session_manager = sess_manager


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Send a message and get a response from the agent.

    Args:
        request: Chat request with session ID and message

    Returns:
        Agent response
    """
    # Verify session exists
    session_data = await session_manager.get_session(request.session_id)

    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    # Get chat history
    chat_history = await session_manager.get_messages(request.session_id, limit=10)

    # Add user message to session
    await session_manager.add_message(
        session_id=request.session_id,
        role="user",
        content=request.message,
    )

    try:
        # Query the agent with optional document filtering
        result = await literature_agent.query_with_history(
            question=request.message,
            chat_history=chat_history,
            document_ids=request.document_ids,
        )

        response_text = result["response"]
        sources = result.get("sources", [])
        confidence = result.get("confidence", 0.0)
        unsupported_spans = result.get("unsupported_spans", [])

        # Add assistant response to session
        await session_manager.add_message(
            session_id=request.session_id,
            role="assistant",
            content=response_text,
            metadata={
                "sources": sources,
                "confidence": confidence,
                "unsupported_spans": unsupported_spans,
            },
        )

        return ChatResponse(
            session_id=request.session_id,
            message=response_text,
            agent_type="literature_reviewer",
            sources=sources,
            confidence=confidence,
            unsupported_spans=unsupported_spans,
            timestamp=datetime.utcnow(),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing request: {str(e)}",
        )
