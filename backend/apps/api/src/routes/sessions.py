"""Session management endpoints."""

from typing import List

from fastapi import APIRouter, HTTPException, status

from ..models.request import CreateSessionRequest
from ..models.response import SessionResponse
from ..services.session_manager import SessionManager

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

# Global instance (will be injected via dependency injection in main.py)
session_manager: SessionManager = None


def set_dependencies(sess_manager: SessionManager) -> None:
    """Set service dependencies.

    Args:
        sess_manager: Session manager instance
    """
    global session_manager
    session_manager = sess_manager


@router.post("", response_model=SessionResponse)
async def create_session(request: CreateSessionRequest) -> SessionResponse:
    """Create a new research session.

    Args:
        request: Session creation request

    Returns:
        Created session data
    """
    session_data = await session_manager.create_session(
        name=request.name,
        topic=request.topic,
        description=request.description,
    )

    return SessionResponse(**session_data)


@router.get("", response_model=List[SessionResponse])
async def list_sessions() -> List[SessionResponse]:
    """List all active sessions.

    Returns:
        List of sessions
    """
    sessions = await session_manager.list_sessions()
    return [SessionResponse(**session) for session in sessions]


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str) -> SessionResponse:
    """Get a specific session by ID.

    Args:
        session_id: Session identifier

    Returns:
        Session data
    """
    session_data = await session_manager.get_session(session_id)

    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    return SessionResponse(**session_data)


@router.delete("/{session_id}")
async def delete_session(session_id: str) -> dict:
    """Delete a session.

    Args:
        session_id: Session identifier

    Returns:
        Success message
    """
    success = await session_manager.delete_session(session_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    return {"message": "Session deleted successfully", "session_id": session_id}


@router.post("/{session_id}/documents/{document_id}")
async def add_document_to_session(session_id: str, document_id: str) -> dict:
    """Add a document to a session.

    Args:
        session_id: Session identifier
        document_id: Document identifier

    Returns:
        Success message
    """
    success = await session_manager.add_document_to_session(session_id, document_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    return {
        "message": "Document added to session",
        "session_id": session_id,
        "document_id": document_id,
    }
