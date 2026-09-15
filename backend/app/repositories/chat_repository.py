from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Sequence

from sqlalchemy import func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_message import ChatMessage


class ChatRepository:
    """Repository for managing ChatMessage persistence."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, message: ChatMessage) -> ChatMessage:
        """Create a new chat message."""
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def get_conversation(self, conversation_id: uuid.UUID, limit: int = 50) -> Sequence[ChatMessage]:
        """Get the messages of a conversation ordered by creation time."""
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_user_conversations(
        self, user_id: uuid.UUID, chat_type: str | None = None, limit: int = 20
    ) -> list[dict[str, Any]]:
        """Get a list of recent conversations for a user with preview of the last message."""
        # Using a window function to get the latest message per conversation
        subq = (
            select(
                ChatMessage,
                func.row_number()
                .over(
                    partition_by=ChatMessage.conversation_id,
                    order_by=desc(ChatMessage.created_at),
                )
                .label("rn"),
            )
            .where(ChatMessage.user_id == user_id)
        )
        
        if chat_type:
            subq = subq.where(ChatMessage.chat_type == chat_type)
            
        subq_alias = subq.subquery()
        
        stmt = (
            select(subq_alias)
            .where(subq_alias.c.rn == 1)
            .order_by(desc(subq_alias.c.created_at))
            .limit(limit)
        )
        
        result = await self.session.execute(stmt)
        rows = result.mappings().all()
        
        conversations = []
        for row in rows:
            conversations.append(
                {
                    "conversation_id": row["conversation_id"],
                    "chat_type": row["chat_type"],
                    "last_message": row["content"][:100] + ("..." if len(row["content"]) > 100 else ""),
                    "created_at": row["created_at"],
                    "prediction_id": row["prediction_id"],
                }
            )
        return conversations

    async def count_user_messages_in_window(
        self, user_id: uuid.UUID, window_seconds: int = 3600
    ) -> int:
        """Count the number of user messages sent within a time window for rate limiting."""
        window_start = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
        stmt = select(func.count(ChatMessage.id)).where(
            ChatMessage.user_id == user_id,
            ChatMessage.role == "user",
            ChatMessage.created_at >= window_start,
        )
        result = await self.session.execute(stmt)
        count = result.scalar()
        return count or 0
