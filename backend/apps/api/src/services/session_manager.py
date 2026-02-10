"""Session management service using Redis."""

import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import redis.asyncio as redis


class SessionManager:
    """Service for managing research sessions with Redis."""

    def __init__(self, redis_url: str, session_expire_hours: int = 24):
        """Initialize session manager.

        Args:
            redis_url: Redis connection URL
            session_expire_hours: Number of hours before sessions expire
        """
        self.redis_url = redis_url
        self.session_expire_seconds = session_expire_hours * 3600
        self.redis_client: Optional[redis.Redis] = None

    async def connect(self) -> None:
        """Connect to Redis."""
        self.redis_client = await redis.from_url(
            self.redis_url, encoding="utf-8", decode_responses=True
        )

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()

    def _session_key(self, session_id: str) -> str:
        """Generate Redis key for session.

        Args:
            session_id: Session identifier

        Returns:
            Redis key string
        """
        return f"session:{session_id}"

    def _messages_key(self, session_id: str) -> str:
        """Generate Redis key for session messages.

        Args:
            session_id: Session identifier

        Returns:
            Redis key string
        """
        return f"session:{session_id}:messages"

    async def create_session(
        self, name: str, topic: Optional[str] = None, description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new research session.

        Args:
            name: Session name
            topic: Optional research topic
            description: Optional session description

        Returns:
            Session data dictionary
        """
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()

        session_data = {
            "session_id": session_id,
            "name": name,
            "topic": topic or "",
            "description": description or "",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "document_ids": [],
            "message_count": 0,
        }

        # Store in Redis
        await self.redis_client.setex(
            self._session_key(session_id),
            self.session_expire_seconds,
            json.dumps(session_data),
        )

        return session_data

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session data or None if not found
        """
        session_json = await self.redis_client.get(self._session_key(session_id))

        if not session_json:
            return None

        return json.loads(session_json)

    async def update_session(self, session_id: str, **kwargs: Any) -> bool:
        """Update session fields.

        Args:
            session_id: Session identifier
            **kwargs: Fields to update

        Returns:
            True if updated, False if session not found
        """
        session_data = await self.get_session(session_id)

        if not session_data:
            return False

        # Update fields
        session_data.update(kwargs)
        session_data["updated_at"] = datetime.utcnow().isoformat()

        # Save back to Redis
        await self.redis_client.setex(
            self._session_key(session_id),
            self.session_expire_seconds,
            json.dumps(session_data),
        )

        return True

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and its messages.

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False if not found
        """
        deleted = await self.redis_client.delete(self._session_key(session_id))
        await self.redis_client.delete(self._messages_key(session_id))

        return deleted > 0

    async def add_message(
        self, session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add a message to a session.

        Args:
            session_id: Session identifier
            role: Message role (user/assistant/system)
            content: Message content
            metadata: Optional metadata for the message

        Returns:
            True if added, False if session not found
        """
        session_data = await self.get_session(session_id)

        if not session_data:
            return False

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }

        # Add to messages list
        await self.redis_client.rpush(self._messages_key(session_id), json.dumps(message))

        # Update session message count
        session_data["message_count"] = session_data.get("message_count", 0) + 1
        await self.update_session(session_id, message_count=session_data["message_count"])

        # Set expiry on messages list
        await self.redis_client.expire(self._messages_key(session_id), self.session_expire_seconds)

        return True

    async def get_messages(
        self, session_id: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get messages from a session.

        Args:
            session_id: Session identifier
            limit: Optional limit on number of messages to retrieve

        Returns:
            List of messages
        """
        if limit:
            messages_json = await self.redis_client.lrange(
                self._messages_key(session_id), -limit, -1
            )
        else:
            messages_json = await self.redis_client.lrange(self._messages_key(session_id), 0, -1)

        return [json.loads(msg) for msg in messages_json]

    async def add_document_to_session(self, session_id: str, document_id: str) -> bool:
        """Associate a document with a session.

        Args:
            session_id: Session identifier
            document_id: Document identifier

        Returns:
            True if added, False if session not found
        """
        session_data = await self.get_session(session_id)

        if not session_data:
            return False

        document_ids = session_data.get("document_ids", [])
        if document_id not in document_ids:
            document_ids.append(document_id)
            await self.update_session(session_id, document_ids=document_ids)

        return True

    async def get_session_documents(self, session_id: str) -> List[str]:
        """Get list of document IDs associated with a session.

        Args:
            session_id: Session identifier

        Returns:
            List of document IDs
        """
        session_data = await self.get_session(session_id)

        if not session_data:
            return []

        return session_data.get("document_ids", [])

    async def list_sessions(self) -> List[Dict[str, Any]]:
        """List all active sessions.

        Returns:
            List of session data dictionaries
        """
        # Get all session keys
        keys = []
        async for key in self.redis_client.scan_iter("session:*"):
            if ":messages" not in key:
                keys.append(key)

        # Retrieve session data
        sessions = []
        for key in keys:
            session_json = await self.redis_client.get(key)
            if session_json:
                sessions.append(json.loads(session_json))

        # Sort by updated_at
        sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)

        return sessions
