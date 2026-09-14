from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SourceReference(BaseModel):
    """Reference to a RAG source document."""
    title: str
    source: str
    relevance: float


class ChatMessageRequest(BaseModel):
    """Request schema for an incoming chat message."""
    message: str = Field(..., min_length=1)
    conversation_id: uuid.UUID | None = None
    language: str = 'en'


class ChatMessageResponse(BaseModel):
    """Response schema for a chat message from the assistant."""
    response: str
    conversation_id: uuid.UUID
    sources: list[SourceReference] | None = None
    disclaimer: str

    model_config = ConfigDict(from_attributes=True)


class ChatMessageDetail(BaseModel):
    """Detailed schema for a chat message in history."""
    id: uuid.UUID
    role: str
    content: str
    sources: dict[str, Any] | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatHistoryResponse(BaseModel):
    """Response schema for a conversation's history."""
    messages: list[ChatMessageDetail]
    conversation_id: uuid.UUID
    total: int


class SummaryRequest(BaseModel):
    """Request schema for generating a prediction summary."""
    language: str = 'en'


class SummaryResponse(BaseModel):
    """Response schema for a prediction summary."""
    summary_text: str
    prediction_id: uuid.UUID
    language: str
    disclaimer: str

    model_config = ConfigDict(from_attributes=True)
