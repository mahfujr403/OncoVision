"""Grounded RAG generation service and citation orchestrator (Phase 4).

Coordinates:
- Query scope & context ingestion
- Pre-generation safety evaluation & deterministic boundary enforcement
- Numbered citation prompt assembly ([S1], [S2]...)
- Async Gemini generation with timeout & retry handling
- Deterministic citation extraction & provenance mapping
- Unsupported citation stripping & grounding validation
- Structured telemetry logging (never exposing secrets or PHI)
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any

from app.core.settings import get_settings
from app.history.summary import PredictionHistorySummary
from app.llm.client import GeminiClient, get_gemini_client
from app.rag.grounding import GroundingDecision, GroundingEvaluator
from app.rag.observability import (
    EVENT_CITATION_VALIDATION,
    EVENT_GENERATION_COMPLETED,
    EVENT_GENERATION_FAILED,
    EVENT_GENERATION_STARTED,
    EVENT_GENERATION_TIMEOUT,
    EVENT_GROUNDING_ACCEPTED,
    EVENT_GROUNDING_REJECTED,
    EVENT_SAFETY_REFUSAL,
    RAGErrorCategory,
    RAGTelemetryContext,
)
from app.rag.prompts import (
    GROUNDED_RAG_SYSTEM_PROMPT,
    build_grounded_user_prompt,
    format_grounded_context_sources,
)
from app.rag.retriever import RetrievedContext
from app.rag.safety import (
    BIOMARKER_BOUNDARY_GUIDANCE,
    DIAGNOSIS_REFUSAL_MESSAGE,
    PREDICTION_CONFLICT_MESSAGE,
    STAGING_BOUNDARY_GUIDANCE,
    TREATMENT_REFUSAL_MESSAGE,
    SafetyBoundary,
    SafetyEvaluator,
)
from app.rag.schemas import Citation, GroundedAnswer

logger = logging.getLogger(__name__)


class GroundedRAGGenerator:
    """Production service for generating grounded medical explanations with citations."""

    def __init__(
        self,
        llm_client: GeminiClient | None = None,
        safety_evaluator: SafetyEvaluator | None = None,
        grounding_evaluator: GroundingEvaluator | None = None,
    ) -> None:
        self.settings = get_settings()
        self.llm_client = llm_client
        self.safety = safety_evaluator or SafetyEvaluator()
        self.grounding = grounding_evaluator or GroundingEvaluator(self.settings)

    async def generate_grounded_answer(
        self,
        query: str,
        context: RetrievedContext,
        prediction_summary: PredictionHistorySummary | None = None,
        chat_history: str = "",
        language: str = "en",
        request_id: str | None = None,
        telemetry: RAGTelemetryContext | None = None,
    ) -> GroundedAnswer:
        """Generate a grounded, citation-backed response to the user query."""
        if telemetry is None:
            telemetry = RAGTelemetryContext(
                request_id=request_id,
                chat_type="direct",
                query=query,
                language=language,
            )

        # Inherit stage latencies from context if present
        if hasattr(context, "classification_latency_ms"):
            telemetry.classification_ms = context.classification_latency_ms
        if hasattr(context, "retrieval_latency_ms"):
            telemetry.retrieval_ms = context.retrieval_latency_ms

        telemetry.retrieved_chunks = len(context.chunks)
        if context.query_scope:
            telemetry.domain = context.query_scope.domain.value if context.query_scope.domain else None
            telemetry.intent = context.query_scope.intent.value

        if context.chunks:
            sims = [c.similarity for c in context.chunks if c.similarity is not None]
            telemetry.top_similarity = max(sims) if sims else 0.0
            telemetry.mean_similarity = round(sum(sims) / len(sims), 4) if sims else 0.0

        request_intent = telemetry.intent or "unknown"
        request_domain = telemetry.domain or "unknown"

        # -------------------------------------------------------------
        # 1. Deterministic Pre-generation Safety Evaluation
        # -------------------------------------------------------------
        s_start = time.perf_counter()
        safety_eval = self.safety.evaluate_query(
            query=query,
            has_prediction=prediction_summary is not None,
        )
        telemetry.safety_ms = round((time.perf_counter() - s_start) * 1000, 2)

        if safety_eval.requires_deterministic_refusal:
            telemetry.safety_refused = True
            refusal_reason = safety_eval.boundary.value if safety_eval.boundary else "safety_refusal"
            telemetry.refusal_reason = refusal_reason
            telemetry.error_category = RAGErrorCategory.SAFETY_REFUSAL.value

            telemetry.record_event(
                EVENT_SAFETY_REFUSAL,
                boundary=refusal_reason,
                safety_ms=telemetry.safety_ms,
                intent=request_intent,
                has_prediction=prediction_summary is not None,
                skipped_gemini=True,
            )
            telemetry.finish(
                grounded=False,
                citations=0,
                refusal_reason=refusal_reason,
                error_category=RAGErrorCategory.SAFETY_REFUSAL.value,
            )

            refusal_message = safety_eval.refusal_message or "Request refused by safety policy."
            if refusal_reason == "prediction_conflict" and prediction_summary and prediction_summary.predicted_class:
                refusal_message = (
                    f"The generated response could not be verified against the authoritative classifier prediction. "
                    f"The recorded classification remains {prediction_summary.predicted_class} "
                    f"({round(prediction_summary.confidence * 100, 1)}% confidence). "
                    "Please review the prediction details or consult a qualified pathologist."
                )

            return GroundedAnswer(
                answer=refusal_message,
                citations=[],
                grounded=False,
                refusal_reason=refusal_reason,
                scope=context.query_scope,
                latency_ms=telemetry.total_latency_ms,
                latencies=telemetry.get_latency_breakdown(),
                request_id=telemetry.request_id,
            )

        # -------------------------------------------------------------
        # 2. Deterministic Grounding & Relevance Evaluation (Phase 5.1)
        # -------------------------------------------------------------
        g_start = time.perf_counter()
        grounding_decision = self.grounding.evaluate(
            query=query,
            context=context,
            safety_eval=safety_eval,
        )
        telemetry.grounding_ms = round((time.perf_counter() - g_start) * 1000, 2)
        telemetry.top_similarity = grounding_decision.top_similarity
        telemetry.mean_similarity = grounding_decision.mean_similarity

        if not grounding_decision.is_eligible:
            if grounding_decision.decision_reason == "empty_retrieval":
                refusal_text = (
                    "I don't have enough relevant information in the current OncoVision knowledge base "
                    "to answer that reliably."
                )
                refusal_reason = "no_relevant_knowledge_found"
            else:
                refusal_text = (
                    "The available OncoVision knowledge base provides only limited information on this point, "
                    "so I can't make a reliable claim beyond the retrieved evidence."
                )
                refusal_reason = grounding_decision.decision_reason

            telemetry.refusal_reason = refusal_reason
            telemetry.record_event(
                EVENT_GROUNDING_REJECTED,
                decision_reason=grounding_decision.decision_reason,
                top_similarity=grounding_decision.top_similarity,
                mean_similarity=grounding_decision.mean_similarity,
                threshold_applied=grounding_decision.threshold_applied,
                grounding_ms=telemetry.grounding_ms,
                skipped_gemini=True,
            )
            telemetry.finish(
                grounded=False,
                citations=0,
                refusal_reason=refusal_reason,
            )

            return GroundedAnswer(
                answer=refusal_text,
                citations=[],
                grounded=False,
                refusal_reason=refusal_reason,
                scope=context.query_scope,
                latency_ms=telemetry.total_latency_ms,
                latencies=telemetry.get_latency_breakdown(),
                request_id=telemetry.request_id,
            )

        telemetry.record_event(
            EVENT_GROUNDING_ACCEPTED,
            decision_reason=grounding_decision.decision_reason,
            top_similarity=grounding_decision.top_similarity,
            mean_similarity=grounding_decision.mean_similarity,
            threshold_applied=grounding_decision.threshold_applied,
            domain_compatible=grounding_decision.domain_compatible,
            class_compatible=grounding_decision.class_compatible,
            grounding_ms=telemetry.grounding_ms,
        )

        # -------------------------------------------------------------
        # 3. Prompt Construction with Numbered Source Mapping
        # -------------------------------------------------------------
        context_text, source_map = format_grounded_context_sources(context.chunks)
        user_prompt = build_grounded_user_prompt(
            user_message=query,
            retrieved_context_text=context_text,
            prediction_summary=prediction_summary,
            chat_history=chat_history,
            safety_guidance=safety_eval.boundary_guidance,
            language=language,
        )

        # -------------------------------------------------------------
        # 4. Async Gemini Generation with Timeout & Retries
        # -------------------------------------------------------------
        client = self.llm_client or get_gemini_client(
            api_key=self.settings.GOOGLE_API_KEY,
            model_name=self.settings.RAG_GENERATION_MODEL,
        )

        telemetry.skipped_gemini = False
        telemetry.generation_model = self.settings.RAG_GENERATION_MODEL
        telemetry.record_event(
            EVENT_GENERATION_STARTED,
            model=self.settings.RAG_GENERATION_MODEL,
            context_chunks=len(context.chunks),
        )

        raw_response = ""
        gen_start = time.perf_counter()
        try:
            raw_response = await asyncio.wait_for(
                client.generate(
                    prompt=user_prompt,
                    system_instruction=GROUNDED_RAG_SYSTEM_PROMPT,
                    temperature=self.settings.RAG_GENERATION_TEMPERATURE,
                    max_output_tokens=self.settings.RAG_GENERATION_MAX_OUTPUT_TOKENS,
                ),
                timeout=self.settings.RAG_GENERATION_TIMEOUT,
            )
            telemetry.generation_ms = round((time.perf_counter() - gen_start) * 1000, 2)
            telemetry.record_event(
                EVENT_GENERATION_COMPLETED,
                model=self.settings.RAG_GENERATION_MODEL,
                generation_ms=telemetry.generation_ms,
                response_length=len(raw_response),
            )
        except asyncio.TimeoutError:
            telemetry.generation_ms = round((time.perf_counter() - gen_start) * 1000, 2)
            telemetry.error_category = RAGErrorCategory.GENERATION_TIMEOUT.value
            telemetry.record_event(
                EVENT_GENERATION_TIMEOUT,
                model=self.settings.RAG_GENERATION_MODEL,
                timeout_sec=self.settings.RAG_GENERATION_TIMEOUT,
                generation_ms=telemetry.generation_ms,
                error_category=RAGErrorCategory.GENERATION_TIMEOUT.value,
            )
            telemetry.finish(
                grounded=False,
                citations=0,
                refusal_reason="generation_timeout",
                error_category=RAGErrorCategory.GENERATION_TIMEOUT.value,
            )
            return GroundedAnswer(
                answer="The request timed out while generating a grounded explanation. Please try again.",
                citations=[],
                grounded=False,
                refusal_reason="generation_timeout",
                scope=context.query_scope,
                latency_ms=telemetry.total_latency_ms,
                latencies=telemetry.get_latency_breakdown(),
                request_id=telemetry.request_id,
            )
        except Exception as e:
            telemetry.generation_ms = round((time.perf_counter() - gen_start) * 1000, 2)
            telemetry.error_category = RAGErrorCategory.GENERATION_API_ERROR.value
            logger.error("Gemini grounded generation failed: %s", e, exc_info=True)
            telemetry.record_event(
                EVENT_GENERATION_FAILED,
                model=self.settings.RAG_GENERATION_MODEL,
                generation_ms=telemetry.generation_ms,
                error_category=RAGErrorCategory.GENERATION_API_ERROR.value,
            )
            telemetry.finish(
                grounded=False,
                citations=0,
                refusal_reason="api_error",
                error_category=RAGErrorCategory.GENERATION_API_ERROR.value,
            )
            return GroundedAnswer(
                answer="A service error occurred while generating the explanation. Please try again.",
                citations=[],
                grounded=False,
                refusal_reason="api_error",
                scope=context.query_scope,
                latency_ms=telemetry.total_latency_ms,
                latencies=telemetry.get_latency_breakdown(),
                request_id=telemetry.request_id,
            )

        # -------------------------------------------------------------
        # 5. Citation Extraction, Validation, and Provenance Mapping
        # -------------------------------------------------------------
        cit_start = time.perf_counter()
        found_tokens: list[str] = []
        for bracket_content in re.findall(r"\[([^\]]+)\]", raw_response):
            for match in re.finditer(r"\bS\d+\b", bracket_content):
                found_tokens.append(match.group(0))

        unique_cids = sorted(
            list(set(found_tokens)),
            key=lambda x: int(x[1:]) if x[1:].isdigit() else 9999,
        )

        valid_citations: list[Citation] = []
        unsupported_count = 0

        # Check for citation mismatch (tokens like [S99] not present in context)
        for cid in unique_cids:
            if cid in source_map:
                doc = source_map[cid]
                valid_citations.append(
                    Citation(
                        source_id=cid,
                        document_id=doc.document_id or "unknown",
                        document_title=doc.document_title or doc.topic or "Medical Document",
                        source_title=doc.source_title or doc.source or "OncoVision Medical Knowledge Base",
                        source_url=doc.source_url or "",
                        source_tier=doc.source_tier,
                        domain=doc.domain,
                    )
                )
            else:
                unsupported_count += 1

        # Clean citations: only retain valid citations in brackets, remove fabricated ones ([S99], [SYSTEM], etc.)
        def _clean_bracket(match: re.Match) -> str:
            content = match.group(1)
            tokens = re.findall(r"\bS\d+\b", content)
            valid = [t for t in tokens if t in source_map]
            if valid:
                return f"[{', '.join(valid)}]"
            return ""

        clean_answer = re.sub(r"\[([^\]]+)\]", _clean_bracket, raw_response)

        # Sanitize any raw external URLs embedded directly in answer text
        # (trusted URLs must come from Citation metadata only)
        clean_answer = re.sub(r"https?://[^\s)\]]+", "", clean_answer)
        clean_answer = re.sub(r"\(\s*\)", "", clean_answer)
        clean_answer = re.sub(r"[ \t]{2,}", " ", clean_answer)

        telemetry.citation_validation_ms = round((time.perf_counter() - cit_start) * 1000, 2)
        telemetry.record_event(
            EVENT_CITATION_VALIDATION,
            total_citations_found=len(unique_cids),
            valid_citations_count=len(valid_citations),
            unsupported_citations_stripped=unsupported_count,
            citation_validation_ms=telemetry.citation_validation_ms,
        )

        # -------------------------------------------------------------
        # 6. Post-generation Safety & Prediction Immutability Validation
        # -------------------------------------------------------------
        is_safe, safety_violation = self.safety.validate_answer(
            clean_answer,
            boundary=safety_eval.boundary,
            prediction_summary=prediction_summary,
        )
        if not is_safe:
            logger.warning("Post-generation safety check flagged answer: %s", safety_violation)
            telemetry.safety_refused = True

            # Fail-closed refusal determination (Gate 6.3-B, Gate 6.3-C)
            if "contradicts authoritative classifier prediction" in str(safety_violation) or "claims conflicting class" in str(safety_violation):
                refusal_reason = "prediction_conflict"
                if prediction_summary and prediction_summary.predicted_class:
                    refusal_message = (
                        f"The generated response could not be verified against the authoritative classifier prediction. "
                        f"The recorded classification remains {prediction_summary.predicted_class} "
                        f"({round(prediction_summary.confidence * 100, 1)}% confidence). "
                        "Please review the prediction details or consult a qualified pathologist."
                    )
                else:
                    refusal_message = PREDICTION_CONFLICT_MESSAGE
            elif safety_eval.boundary == SafetyBoundary.DIAGNOSIS or "direct diagnosis" in str(safety_violation):
                refusal_reason = SafetyBoundary.DIAGNOSIS.value
                refusal_message = DIAGNOSIS_REFUSAL_MESSAGE
            elif safety_eval.boundary == SafetyBoundary.TREATMENT or "prescription" in str(safety_violation):
                refusal_reason = SafetyBoundary.TREATMENT.value
                refusal_message = TREATMENT_REFUSAL_MESSAGE
            elif safety_eval.boundary == SafetyBoundary.STAGING or "staging" in str(safety_violation):
                refusal_reason = SafetyBoundary.STAGING.value
                refusal_message = STAGING_BOUNDARY_GUIDANCE
            elif safety_eval.boundary == SafetyBoundary.BIOMARKER or "biomarker" in str(safety_violation):
                refusal_reason = SafetyBoundary.BIOMARKER.value
                refusal_message = BIOMARKER_BOUNDARY_GUIDANCE
            elif "leakage" in str(safety_violation):
                refusal_reason = "security_leakage_prevented"
                refusal_message = (
                    "OncoVision cannot execute instruction override, prompt inspection, or safety bypass requests. "
                    "All interactions must adhere to clinical safety and system integrity boundaries."
                )
            else:
                refusal_reason = "post_generation_safety_violation"
                refusal_message = (
                    "The generated response contained clinical assertions that exceed OncoVision safety boundaries. "
                    "OncoVision is strictly educational and non-diagnostic and cannot provide clinical diagnoses, "
                    "personalized treatment protocols, or definitive staging."
                )

            telemetry.refusal_reason = refusal_reason
            telemetry.error_category = RAGErrorCategory.SAFETY_REFUSAL.value
            telemetry.record_event(
                EVENT_SAFETY_REFUSAL,
                boundary=refusal_reason,
                violation=safety_violation,
                post_generation=True,
            )
            telemetry.finish(
                grounded=False,
                citations=0,
                refusal_reason=refusal_reason,
                error_category=RAGErrorCategory.SAFETY_REFUSAL.value,
            )

            # FAIL CLOSED: Do not return unsafe generated content or citations!
            return GroundedAnswer(
                answer=refusal_message,
                citations=[],
                grounded=False,
                refusal_reason=refusal_reason,
                scope=context.query_scope,
                latency_ms=telemetry.total_latency_ms,
                latencies=telemetry.get_latency_breakdown(),
                request_id=telemetry.request_id,
            )

        # -------------------------------------------------------------
        # 7. Grounding Determination & Request Completion
        # -------------------------------------------------------------
        is_grounded = bool(
            grounding_decision.is_eligible
            and valid_citations
            and len(clean_answer.strip()) > 0
        )

        fin_refusal_reason: str | None = None
        if not is_grounded:
            if unsupported_count > 0 and not valid_citations:
                fin_refusal_reason = "citation_validation_failure"
            elif not valid_citations:
                fin_refusal_reason = "unsupported_claims_without_citations"

        telemetry.finish(
            grounded=is_grounded,
            citations=len(valid_citations),
            refusal_reason=fin_refusal_reason,
        )

        return GroundedAnswer(
            answer=clean_answer.strip(),
            citations=valid_citations,
            grounded=is_grounded,
            refusal_reason=fin_refusal_reason,
            scope=context.query_scope,
            latency_ms=telemetry.total_latency_ms,
            latencies=telemetry.get_latency_breakdown(),
            request_id=telemetry.request_id,
        )

