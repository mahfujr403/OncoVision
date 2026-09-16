from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies.auth import get_current_active_user
from app.models.user import User
from app.schemas.chat import SummaryRequest, SummaryResponse
from app.services.llm_summary_service import LLMSummaryService
from app.utils.response import success_response, error_response
from app.constants.app import TAG_AI_SUMMARY

router = APIRouter(prefix="/predictions", tags=[TAG_AI_SUMMARY])


@router.post("/{prediction_id}/summary", response_model=dict[str, Any])
async def generate_summary(
    prediction_id: uuid.UUID,
    request: SummaryRequest = SummaryRequest(),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Generate or retrieve a cached AI summary for a prediction."""
    service = LLMSummaryService(db)
    try:
        result = await service.generate_summary(
            prediction_id=prediction_id,
            user_id=current_user.id,
            language=request.language
        )
        return success_response(data=result, message="Summary generated successfully")
    except ValueError as e:
        return error_response(message=str(e), status_code=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return error_response(message=f"An error occurred: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get("/{prediction_id}/summary", response_model=dict[str, Any])
async def get_summary(
    prediction_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve an existing AI summary for a prediction without regenerating it."""
    service = LLMSummaryService(db)
    try:
        # Re-using generate_summary which fetches cache if present
        # If caching logic is updated to strictly fetch, we could split it.
        result = await service.generate_summary(
            prediction_id=prediction_id,
            user_id=current_user.id,
        )
        return success_response(data=result, message="Summary retrieved successfully")
    except ValueError as e:
        return error_response(message=str(e), status_code=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return error_response(message=f"An error occurred: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
