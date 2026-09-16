"""Chat service for prediction-specific and RAG knowledge conversations
(Phase 11 — LLM + RAG Integration).

Orchestrates: user message persistence → prompt assembly → Gemini LLM
call → assistant response persistence. Enforces per-user rate limits
via ``ChatRepository.count_user_messages_in_window``.
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
from app.llm.prompts import (
    KNOWLEDGE_CHAT_SYSTEM_PROMPT,
    KNOWLEDGE_CHAT_USER_PROMPT_TEMPLATE,
    PREDICTION_CHAT_SYSTEM_PROMPT,
    PREDICTION_CHAT_USER_PROMPT_TEMPLATE,
)
from app.models.chat_message import ChatMessage
from app.models.prediction_history import PredictionHistoryRecord
from app.rag.embeddings import EmbeddingService
from app.rag.retriever import RAGRetriever
from app.repositories.chat_repository import ChatRepository

logger = logging.getLogger(__name__)
settings = get_settings()

_MEDICAL_DISCLAIMER = (
    "This information is AI-generated for educational purposes only. "
    "It is not medical advice or a diagnosis. Always consult a qualified "
    "healthcare professional for clinical decisions."
)


class ChatService:
    """Service for handling prediction-specific and RAG knowledge chats."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ChatRepository(session)

    async def _check_rate_limit(self, user_id: uuid.UUID) -> None:
        """Raise ``ValueError`` if the user has exceeded the rate limit."""
        count = await self.repo.count_user_messages_in_window(
            user_id,
            window_seconds=settings.CHAT_RATE_LIMIT_WINDOW_SECONDS,
        )
        if count >= settings.CHAT_RATE_LIMIT_MAX_REQUESTS:
            raise ValueError(
                f"Rate limit exceeded. Maximum {settings.CHAT_RATE_LIMIT_MAX_REQUESTS} "
                f"messages per {settings.CHAT_RATE_LIMIT_WINDOW_SECONDS // 60} minutes."
            )

    # ------------------------------------------------------------------
    # Prediction-specific chat
    # ------------------------------------------------------------------

    async def prediction_chat(
        self,
        user_id: uuid.UUID,
        prediction_id: uuid.UUID,
        message: str,
        conversation_id: uuid.UUID | None,
        language: str = "en",
    ) -> dict[str, Any]:
        """Handle a chat message about a specific prediction result."""
        await self._check_rate_limit(user_id)

        # Verify the prediction exists and belongs to this user (matches id or request_id)
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
            raise ValueError("Prediction not found or access denied.")

        conv_id = conversation_id or uuid.uuid4()

        # Persist the user message using the verified prediction.id
        user_msg = ChatMessage(
            conversation_id=conv_id,
            user_id=user_id,
            prediction_id=prediction.id,
            role="user",
            content=message,
            chat_type="prediction",
        )
        await self.repo.create(user_msg)

        # Build context from the prediction record
        class_probs = ""
        if prediction.summary and isinstance(prediction.summary, dict):
            probs = prediction.summary.get("class_probabilities", {})
            if probs:
                class_probs = json.dumps(probs, indent=2)

        prediction_context = (
            f"Predicted Class: {prediction.predicted_class}\n"
            f"Confidence: {round((prediction.confidence or 0) * 100, 2)}%\n"
            f"Model Agreement: {round((prediction.agreement_ratio or 0) * 100, 2)}%\n"
            f"Participating Models: {prediction.participating_models}\n"
            f"Class Probabilities:\n{class_probs}"
        )

        # Build chat history string with rollback safety
        chat_history = ""
        try:
            history_records = await self.repo.get_conversation(conv_id, limit=20)
            chat_history = "\n".join(
                f"{msg.role.capitalize()}: {msg.content}" for msg in history_records
            )
        except Exception as e:
            logger.warning("Failed to fetch chat history: %s", e)
            try:
                await self.session.rollback()
            except Exception:
                pass

        # Assemble the prompt
        prompt = PREDICTION_CHAT_USER_PROMPT_TEMPLATE.format(
            prediction_context=prediction_context,
            chat_history=chat_history,
            user_message=message,
        )

        # Call the LLM
        client = get_gemini_client(
            api_key=settings.GOOGLE_API_KEY,
            model_name=settings.LLM_MODEL,
        )
        lang_instruction = (
            f"\n\nPlease respond in {'Bangla' if language == 'bn' else 'English'}."
        )
        response_text = await client.generate(
            prompt=prompt,
            system_instruction=PREDICTION_CHAT_SYSTEM_PROMPT + lang_instruction,
            temperature=settings.LLM_TEMPERATURE,
            max_output_tokens=settings.LLM_MAX_TOKENS,
        )

        # Persist the assistant response using verified prediction.id with rollback safety
        try:
            assistant_msg = ChatMessage(
                conversation_id=conv_id,
                user_id=user_id,
                prediction_id=prediction.id,
                role="assistant",
                content=response_text,
                chat_type="prediction",
            )
            await self.repo.create(assistant_msg)
        except Exception as e:
            logger.warning("Failed to persist assistant message: %s", e)
            try:
                await self.session.rollback()
            except Exception:
                pass

        return {
            "response": response_text,
            "conversation_id": str(conv_id),
            "disclaimer": _MEDICAL_DISCLAIMER,
        }

    # ------------------------------------------------------------------
    # RAG-powered knowledge chat
    # ------------------------------------------------------------------

    async def knowledge_chat(
        self,
        user_id: uuid.UUID,
        message: str,
        conversation_id: uuid.UUID | None,
        language: str = "en",
    ) -> dict[str, Any]:
        """Handle a general cancer knowledge question via RAG retrieval."""
        await self._check_rate_limit(user_id)

        conv_id = conversation_id or uuid.uuid4()

        # Persist the user message
        user_msg = ChatMessage(
            conversation_id=conv_id,
            user_id=user_id,
            prediction_id=None,
            role="user",
            content=message,
            chat_type="knowledge",
        )
        await self.repo.create(user_msg)

        # Build chat history string with rollback safety first so we can support conversational context
        chat_history = ""
        last_user_query = ""
        try:
            history_records = await self.repo.get_conversation(conv_id, limit=8)
            if history_records:
                chat_history = "\n".join(
                    f"{msg.role.capitalize()}: {msg.content}" for msg in history_records
                )
                past_user_msgs = [m.content for m in history_records if m.role == "user" and m.content != message]
                if past_user_msgs:
                    last_user_query = past_user_msgs[-1]
        except Exception as e:
            logger.warning("Failed to fetch chat history: %s", e)
            try:
                await self.session.rollback()
            except Exception:
                pass

        # Context-aware RAG retrieval query for multi-turn follow-ups
        retrieval_query = message
        lower_msg = message.lower()
        needs_context = (
            len(message.split()) <= 6
            or any(kw in lower_msg for kw in ["him", "his", "he", "developer", "creator", "contact", "email", "github", "linkedin", "portfolio", "reach", "provide", "give", "who", "it", "they"])
        )
        if needs_context and last_user_query:
            retrieval_query = f"{last_user_query} {message}"

        # RAG retrieval with graceful fallback
        retrieved_docs = []
        try:
            embedding_service = EmbeddingService(
                get_gemini_client(
                    api_key=settings.GOOGLE_API_KEY,
                    model_name=settings.LLM_MODEL,
                )
            )
            retriever = RAGRetriever(
                session=self.session,
                embedding_service=embedding_service,
            )
            retrieved_docs = await retriever.retrieve(
                query=retrieval_query,
                top_k=settings.RAG_TOP_K,
                similarity_threshold=settings.RAG_SIMILARITY_THRESHOLD,
            )
            retrieved_context = retriever.format_context(retrieved_docs)
        except Exception as e:
            logger.warning("RAG retrieval failed, falling back to general LLM response: %s", e)
            retrieved_context = "No relevant context found."

        sources = [
            {
                "title": doc.topic,
                "source": doc.source,
                "relevance": round(doc.similarity, 4),
            }
            for doc in retrieved_docs
        ]

        # Assemble the prompt
        prompt = KNOWLEDGE_CHAT_USER_PROMPT_TEMPLATE.format(
            retrieved_context=retrieved_context,
            chat_history=chat_history,
            user_message=message,
        )

        # Call the LLM
        client = get_gemini_client(
            api_key=settings.GOOGLE_API_KEY,
            model_name=settings.LLM_MODEL,
        )
        lang_instruction = (
            f"\n\nPlease respond in {'Bangla' if language == 'bn' else 'English'}."
        )
        response_text = await client.generate(
            prompt=prompt,
            system_instruction=KNOWLEDGE_CHAT_SYSTEM_PROMPT + lang_instruction,
            temperature=settings.LLM_TEMPERATURE,
            max_output_tokens=settings.LLM_MAX_TOKENS,
        )

        # Persist the assistant response with rollback safety
        try:
            assistant_msg = ChatMessage(
                conversation_id=conv_id,
                user_id=user_id,
                prediction_id=None,
                role="assistant",
                content=response_text,
                chat_type="knowledge",
                sources={"sources": sources},
            )
            await self.repo.create(assistant_msg)
        except Exception as e:
            logger.warning("Failed to persist assistant response: %s", e)
            try:
                await self.session.rollback()
            except Exception:
                pass

        return {
            "response": response_text,
            "conversation_id": str(conv_id),
            "sources": sources,
            "disclaimer": _MEDICAL_DISCLAIMER,
        }
