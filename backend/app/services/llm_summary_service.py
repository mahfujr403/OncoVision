"""LLM summary generation service (Phase 11 — LLM + RAG Integration).

Generates human-readable summaries of prediction results using the
Gemini API. Summaries are cached on the ``ai_summary`` column of
``PredictionHistoryRecord`` so subsequent requests are served from the
database without an additional LLM call.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.llm.client import get_gemini_client
from app.llm.prompts import SUMMARY_SYSTEM_PROMPT, SUMMARY_USER_PROMPT_TEMPLATE
from app.models.prediction_history import PredictionHistoryRecord

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMSummaryService:
    """Service for generating LLM-powered prediction summaries."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def generate_summary(
        self,
        prediction_id: uuid.UUID,
        user_id: uuid.UUID,
        language: str = "en",
    ) -> dict[str, Any]:
        """Generate or retrieve a cached summary for a prediction.

        Args:
            prediction_id: The UUID of the prediction to summarize (matches id or request_id).
            user_id: The UUID of the requesting user (ownership check).
            language: Output language — ``'en'`` for English, ``'bn'`` for Bangla.

        Returns:
            A dict containing ``summary_text``, ``prediction_id``,
            ``language``, and a ``disclaimer`` string.

        Raises:
            ValueError: If the prediction does not exist or the user
                does not own it.
        """
        stmt = select(PredictionHistoryRecord).where(
            or_(
                PredictionHistoryRecord.id == prediction_id,
                PredictionHistoryRecord.request_id == str(prediction_id),
            ),
            PredictionHistoryRecord.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        prediction = result.scalar_one_or_none()

        if prediction is None:
            raise ValueError("Prediction not found or you do not have access to it.")

        # Return cached summary if available
        if getattr(prediction, "ai_summary", None):
            return {
                "summary_text": prediction.ai_summary,
                "prediction_id": str(prediction.id),
                "language": language,
                "disclaimer": (
                    "This is an AI-generated summary for informational purposes "
                    "only. It is not a medical diagnosis. Please consult a qualified "
                    "healthcare professional for clinical advice."
                ),
            }

        # Build the class probabilities string from the summary JSONB
        class_probabilities = "N/A"
        if prediction.summary and isinstance(prediction.summary, dict):
            probs = prediction.summary.get("class_probabilities", {})
            if probs:
                class_probabilities = json.dumps(probs, indent=2)

        # Build the prompt
        prompt = SUMMARY_USER_PROMPT_TEMPLATE.format(
            predicted_class=prediction.predicted_class or "Unknown",
            confidence_pct=round((prediction.confidence or 0) * 100, 2),
            agreement_pct=round((prediction.agreement_ratio or 0) * 100, 2),
            participating_models=prediction.participating_models or 0,
            class_probabilities=class_probabilities,
            language="Bangla" if language == "bn" else "English",
        )

        # Call Gemini
        client = get_gemini_client(
            api_key=settings.GOOGLE_API_KEY,
            model_name=settings.LLM_MODEL,
        )
        summary_text = await client.generate(
            prompt=prompt,
            system_instruction=SUMMARY_SYSTEM_PROMPT,
            temperature=settings.LLM_TEMPERATURE,
            max_output_tokens=settings.LLM_MAX_TOKENS,
        )

        # Cache the summary in the database
        try:
            prediction.ai_summary = summary_text
            self.session.add(prediction)
            await self.session.commit()
        except Exception:
            logger.warning(
                "Failed to cache AI summary for prediction %s — "
                "the ai_summary column may not exist yet.",
                prediction_id,
                exc_info=True,
            )
            await self.session.rollback()

        return {
            "summary_text": summary_text,
            "prediction_id": str(prediction.id),
            "language": language,
            "disclaimer": (
                "This is an AI-generated summary for informational purposes "
                "only. It is not a medical diagnosis. Please consult a qualified "
                "healthcare professional for clinical advice."
            ),
        }
