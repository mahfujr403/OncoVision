from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.database.session import get_db
from app.dependencies.auth import get_current_active_user
from app.models.user import User
from app.repositories.chat_repository import ChatRepository
from app.schemas.chat import ChatHistoryResponse, ChatMessageRequest, ChatMessageResponse, ChatMessageDetail
from app.services.chat_service import ChatService
from app.utils.response import success_response, error_response
from app.constants.app import TAG_AI_CHAT

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=[TAG_AI_CHAT])


@router.post("/prediction/{prediction_id}", response_model=dict[str, Any])
async def prediction_chat_endpoint(
    prediction_id: uuid.UUID,
    request: ChatMessageRequest,
    raw_request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Chat about a specific prediction."""
    request_id = getattr(raw_request.state, "request_id", None) or raw_request.headers.get("X-Request-ID")
    service = ChatService(db)
    try:
        result = await service.prediction_chat(
            user_id=current_user.id,
            prediction_id=prediction_id,
            message=request.message,
            conversation_id=request.conversation_id,
            language=request.language,
            request_id=request_id,
        )
        return success_response(data=result, message="Message sent successfully")
    except ValueError as e:
        return error_response(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error("Error in prediction chat endpoint: %s", e, exc_info=True)
        return error_response(
            message="An error occurred while processing the request. Please try again.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/prediction/{prediction_id}/stream")
async def prediction_chat_stream_endpoint(
    prediction_id: uuid.UUID,
    request: ChatMessageRequest,
    raw_request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> EventSourceResponse:
    """Stream chat response about a specific prediction result via SSE."""
    request_id = getattr(raw_request.state, "request_id", None) or raw_request.headers.get("X-Request-ID")
    service = ChatService(db)
    generator = service.stream_prediction_chat(
        user_id=current_user.id,
        prediction_id=prediction_id,
        message=request.message,
        conversation_id=request.conversation_id,
        language=request.language,
        request_id=request_id,
        raw_request=raw_request,
    )
    return EventSourceResponse(
        generator,
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/knowledge", response_model=dict[str, Any])
async def knowledge_chat_endpoint(
    request: ChatMessageRequest,
    raw_request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """RAG-powered knowledge chat."""
    request_id = getattr(raw_request.state, "request_id", None) or raw_request.headers.get("X-Request-ID")
    service = ChatService(db)
    try:
        result = await service.knowledge_chat(
            user_id=current_user.id,
            message=request.message,
            conversation_id=request.conversation_id,
            language=request.language,
            request_id=request_id,
        )
        return success_response(data=result, message="Message sent successfully")
    except ValueError as e:
        return error_response(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error("Error in knowledge chat endpoint: %s", e, exc_info=True)
        return error_response(
            message="An error occurred while processing the request. Please try again.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/knowledge/stream")
async def knowledge_chat_stream_endpoint(
    request: ChatMessageRequest,
    raw_request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> EventSourceResponse:
    """Stream RAG-powered knowledge chat response via SSE."""
    request_id = getattr(raw_request.state, "request_id", None) or raw_request.headers.get("X-Request-ID")
    service = ChatService(db)
    generator = service.stream_knowledge_chat(
        user_id=current_user.id,
        message=request.message,
        conversation_id=request.conversation_id,
        language=request.language,
        request_id=request_id,
        raw_request=raw_request,
    )
    return EventSourceResponse(
        generator,
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )



@router.get("/history/{conversation_id}", response_model=dict[str, Any])
async def get_chat_history(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get the chat history for a specific conversation."""
    repo = ChatRepository(db)
    messages = await repo.get_conversation(conversation_id, user_id=current_user.id)
    
    if not messages:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    details = [
        ChatMessageDetail.model_validate(msg) for msg in messages
    ]
    
    result = ChatHistoryResponse(
        messages=details,
        conversation_id=conversation_id,
        total=len(details)
    )
    return success_response(data=result.model_dump(mode="json"), message="Chat history retrieved")
