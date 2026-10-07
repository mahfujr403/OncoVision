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
from app.history.summary import PredictionHistorySummary
from app.models.chat_message import ChatMessage
from app.models.prediction_history import PredictionHistoryRecord
from app.rag.classifier import QueryScopeClassifier
from app.rag.embeddings import EmbeddingService
from app.rag.generator import GroundedRAGGenerator
from app.rag.observability import RAGTelemetryContext
from app.rag.retriever import RAGRetriever, RetrievedContext
from app.rag.schemas import GroundedAnswer
from app.repositories.chat_repository import ChatRepository

logger = logging.getLogger(__name__)
settings = get_settings()

_MEDICAL_DISCLAIMER = (
    "This information is AI-generated for educational and research purposes only. "
    "It is not medical advice, a pathological diagnosis, or a treatment recommendation. "
    "Always consult a qualified oncologist or board-certified pathologist for clinical decisions."
)


class ChatService:
    """Service for handling prediction-specific and RAG knowledge chats (Phase 4)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ChatRepository(session)
        self.classifier = QueryScopeClassifier()
        self.generator = GroundedRAGGenerator()

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
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """Handle a chat message about a specific prediction result."""
        telemetry = RAGTelemetryContext(
            request_id=request_id,
            chat_type="prediction",
            query=message,
            language=language,
        )
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

        if conversation_id is not None:
            conv_meta = await self.repo.get_conversation_metadata(conversation_id)
            if (
                conv_meta is None
                or conv_meta["user_id"] != user_id
                or conv_meta["chat_type"] != "prediction"
                or conv_meta["prediction_id"] != prediction.id
            ):
                raise ValueError("Conversation not found or access denied.")
            conv_id = conversation_id
        else:
            conv_id = uuid.uuid4()

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

        # Extract immutable PredictionHistorySummary from record
        pred_summary: PredictionHistorySummary | None = None
        if prediction.summary and isinstance(prediction.summary, dict):
            try:
                pred_summary = PredictionHistorySummary.model_validate(prediction.summary)
            except Exception as pe:
                logger.debug("Could not parse prediction.summary into PredictionHistorySummary: %s", pe)

        if pred_summary is None:
            # Fallback construct minimal immutable summary from row fields
            pred_summary = PredictionHistorySummary(
                predicted_class=prediction.predicted_class,
                confidence=prediction.confidence or 0.0,
                agreement_ratio=prediction.agreement_ratio or 0.0,
                participating_models=[],
                successful_models=[],
                failed_models=[],
            )

        # Build chat history string with rollback safety
        chat_history = ""
        try:
            history_records = await self.repo.get_conversation(conv_id, user_id=user_id, limit=20)
            chat_history = "\n".join(
                f"{msg.role.capitalize()}: {msg.content}" for msg in history_records
            )
        except Exception as e:
            logger.warning("Failed to fetch chat history: %s", e)
            try:
                await self.session.rollback()
            except Exception:
                pass

        # Check deterministic safety boundary before retrieval (Phase 5.3)
        pre_safety = self.generator.safety.evaluate_query(message, has_prediction=True)
        retrieved_context = None

        if pre_safety.requires_deterministic_refusal:
            scope = self.classifier.classify(message)
            retrieved_context = RetrievedContext(
                chunks=[],
                query_scope=scope,
                reason="safety_refusal",
            )
        else:
            # Retrieve relevant histopathology knowledge for this predicted class
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
                    classifier=self.classifier,
                    safety_evaluator=self.generator.safety,
                )
                retrieval_query = f"{prediction.predicted_class} histopathology {message}"
                retrieved_context = await retriever.retrieve_context(
                    query=retrieval_query,
                    top_k=settings.RAG_TOP_K,
                    similarity_threshold=settings.RAG_SIMILARITY_THRESHOLD,
                    telemetry=telemetry,
                )
            except Exception as re_err:
                logger.warning("Knowledge retrieval failed for prediction chat: %s", re_err)
                scope = self.classifier.classify(message)
                retrieved_context = RetrievedContext(
                    chunks=[],
                    query_scope=scope,
                    reason="retrieval_exception",
                )

        # Generate grounded response enforcing prediction & safety boundaries
        grounded_answer = await self.generator.generate_grounded_answer(
            query=message,
            context=retrieved_context,
            prediction_summary=pred_summary,
            chat_history=chat_history,
            language=language,
            telemetry=telemetry,
        )

        sources = [
            {
                "title": doc.source_title or doc.topic,
                "source": doc.source,
                "relevance": round(doc.similarity, 4),
                "url": doc.source_url,
                "tier": doc.source_tier,
                "citation": doc.citation,
                "document_title": doc.document_title,
            }
            for doc in retrieved_context.chunks
        ] if grounded_answer.grounded else []

        # Persist the assistant response using verified prediction.id with rollback safety
        try:
            assistant_msg = ChatMessage(
                conversation_id=conv_id,
                user_id=user_id,
                prediction_id=prediction.id,
                role="assistant",
                content=grounded_answer.answer,
                chat_type="prediction",
                sources={"sources": sources, "citations": [c.model_dump() for c in grounded_answer.citations]},
            )
            await self.repo.create(assistant_msg)
        except Exception as e:
            logger.warning("Failed to persist assistant message: %s", e)
            try:
                await self.session.rollback()
            except Exception:
                pass

        scope_dict = None
        if grounded_answer.scope:
            scope_dict = {
                "domain": grounded_answer.scope.domain.value if grounded_answer.scope.domain else None,
                "intent": grounded_answer.scope.intent.value,
                "class_scopes": [cs.value for cs in grounded_answer.scope.class_scopes],
            }

        return {
            "response": grounded_answer.answer,
            "conversation_id": str(conv_id),
            "sources": sources,
            "citations": [c.model_dump() for c in grounded_answer.citations],
            "grounded": grounded_answer.grounded,
            "scope": scope_dict,
            "disclaimer": grounded_answer.disclaimer,
            "request_id": telemetry.request_id,
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
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """Handle a general cancer knowledge question via RAG retrieval."""
        telemetry = RAGTelemetryContext(
            request_id=request_id,
            chat_type="knowledge",
            query=message,
            language=language,
        )
        await self._check_rate_limit(user_id)

        if conversation_id is not None:
            conv_meta = await self.repo.get_conversation_metadata(conversation_id)
            if (
                conv_meta is None
                or conv_meta["user_id"] != user_id
                or conv_meta["chat_type"] != "knowledge"
            ):
                raise ValueError("Conversation not found or access denied.")
            conv_id = conversation_id
        else:
            conv_id = uuid.uuid4()

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

        # Build chat history string with rollback safety
        chat_history = ""
        last_user_query = ""
        try:
            history_records = await self.repo.get_conversation(conv_id, user_id=user_id, limit=8)
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

        # Check deterministic safety boundary before retrieval (Phase 5.3)
        pre_safety = self.generator.safety.evaluate_query(message, has_prediction=False)
        retrieved_context: RetrievedContext | None = None

        if pre_safety.requires_deterministic_refusal:
            scope = self.classifier.classify(retrieval_query)
            retrieved_context = RetrievedContext(
                chunks=[],
                query_scope=scope,
                reason="safety_refusal",
            )
        else:
            # Two-stage RAG retrieval with QueryScopeClassifier
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
                    classifier=self.classifier,
                    safety_evaluator=self.generator.safety,
                )
                retrieved_context = await retriever.retrieve_context(
                    query=retrieval_query,
                    top_k=settings.RAG_TOP_K,
                    similarity_threshold=settings.RAG_SIMILARITY_THRESHOLD,
                    telemetry=telemetry,
                )
            except Exception as e:
                logger.warning("RAG retrieval failed: %s", e)
                scope = self.classifier.classify(retrieval_query)
                retrieved_context = RetrievedContext(
                    chunks=[],
                    query_scope=scope,
                    reason="retrieval_exception",
                )

        # Grounded generation with deterministic safety enforcement and citations
        grounded_answer = await self.generator.generate_grounded_answer(
            query=message,
            context=retrieved_context,
            chat_history=chat_history,
            language=language,
            telemetry=telemetry,
        )

        sources = [
            {
                "title": doc.source_title or doc.topic,
                "source": doc.source,
                "relevance": round(doc.similarity, 4),
                "url": doc.source_url,
                "tier": doc.source_tier,
                "citation": doc.citation,
                "document_title": doc.document_title,
            }
            for doc in retrieved_context.chunks
        ] if grounded_answer.grounded else []

        # Persist the assistant response with rollback safety
        try:
            assistant_msg = ChatMessage(
                conversation_id=conv_id,
                user_id=user_id,
                prediction_id=None,
                role="assistant",
                content=grounded_answer.answer,
                chat_type="knowledge",
                sources={"sources": sources, "citations": [c.model_dump() for c in grounded_answer.citations]},
            )
            await self.repo.create(assistant_msg)
        except Exception as e:
            logger.warning("Failed to persist assistant response: %s", e)
            try:
                await self.session.rollback()
            except Exception:
                pass

        scope_dict = None
        if grounded_answer.scope:
            scope_dict = {
                "domain": grounded_answer.scope.domain.value if grounded_answer.scope.domain else None,
                "intent": grounded_answer.scope.intent.value,
                "class_scopes": [cs.value for cs in grounded_answer.scope.class_scopes],
            }

        return {
            "response": grounded_answer.answer,
            "conversation_id": str(conv_id),
            "sources": sources,
            "citations": [c.model_dump() for c in grounded_answer.citations],
            "grounded": grounded_answer.grounded,
            "scope": scope_dict,
            "disclaimer": grounded_answer.disclaimer,
            "request_id": telemetry.request_id,
        }


