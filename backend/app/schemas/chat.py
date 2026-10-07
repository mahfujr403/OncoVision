from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.settings import get_settings
from app.rag.schemas import Citation


class SourceReference(BaseModel):
    """Reference to a RAG source document."""
    title: str
    source: str
    relevance: float
    url: str | None = None
    tier: int | None = None


class ChatMessageRequest(BaseModel):
    """Request schema for an incoming chat message."""
    message: str = Field(..., min_length=1, max_length=2000)
    conversation_id: uuid.UUID | None = None
    language: str = Field(default="en", max_length=10)

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Message cannot be empty or whitespace only.")
        max_len = get_settings().CHAT_MAX_MESSAGE_LENGTH
        if len(v) > max_len:
            raise ValueError(f"Message exceeds maximum allowed length of {max_len} characters.")
        return trimmed


class ChatMessageResponse(BaseModel):
    """Response schema for a chat message from the assistant."""
    response: str
    conversation_id: uuid.UUID
    sources: list[SourceReference] | None = None
    disclaimer: str
    grounded: bool | None = None
    citations: list[Citation] | None = None
    scope: dict[str, Any] | None = None

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
