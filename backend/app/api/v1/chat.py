from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies.auth import get_current_active_user
from app.models.user import User
from app.repositories.chat_repository import ChatRepository
from app.schemas.chat import ChatHistoryResponse, ChatMessageRequest, ChatMessageResponse, ChatMessageDetail
from app.services.chat_service import ChatService
from app.utils.response import success_response
from app.constants.app import TAG_AI_CHAT

router = APIRouter(prefix="/chat", tags=[TAG_AI_CHAT])


@router.post("/prediction/{prediction_id}", response_model=dict[str, Any])
async def prediction_chat_endpoint(
    prediction_id: uuid.UUID,
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Chat about a specific prediction."""
    service = ChatService(db)
    try:
        result = await service.prediction_chat(
            user_id=current_user.id,
            prediction_id=prediction_id,
            message=request.message,
            conversation_id=request.conversation_id,
            language=request.language
        )
        return success_response(data=result, message="Message sent successfully")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/knowledge", response_model=dict[str, Any])
async def knowledge_chat_endpoint(
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """RAG-powered knowledge chat."""
    service = ChatService(db)
    try:
        result = await service.knowledge_chat(
            user_id=current_user.id,
            message=request.message,
            conversation_id=request.conversation_id,
            language=request.language
        )
        return success_response(data=result, message="Message sent successfully")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/history/{conversation_id}", response_model=dict[str, Any])
async def get_chat_history(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get the chat history for a specific conversation."""
    repo = ChatRepository(db)
    messages = await repo.get_conversation(conversation_id)
    
    if messages and messages[0].user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    details = [
        ChatMessageDetail.model_validate(msg) for msg in messages
    ]
    
    result = ChatHistoryResponse(
        messages=details,
        conversation_id=conversation_id,
        total=len(details)
    )
    return success_response(data=result.model_dump(mode="json"), message="Chat history retrieved")
