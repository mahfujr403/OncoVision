"""Deterministic safety enforcement and clinical boundary management (Phase 4).

Guarantees that:
1. The LLM never becomes a medical classifier or diagnostic engine.
2. Direct personal diagnosis requests ("Do I have cancer?") are refused deterministically.
3. Personal treatment/chemotherapy prescription requests are refused deterministically.
4. Histopathology image staging boundaries are strictly preserved.
5. H&E molecular biomarker boundaries are enforced.
6. Predictions from the ML classifier are preserved without modification.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.history.summary import PredictionHistorySummary


class SafetyBoundary(str, Enum):
    """Recognized clinical safety boundary categories."""

    DIAGNOSIS = "diagnosis_boundary"
    TREATMENT = "treatment_boundary"
    STAGING = "staging_boundary"
    BIOMARKER = "biomarker_boundary"
    CLASSIFIER = "classifier_boundary"
    INJECTION = "prompt_injection_boundary"
    PREDICTION_OVERRIDE = "prediction_conflict"


class SafetyEvaluation(BaseModel):
    """Result of deterministic pre-generation safety evaluation."""

    boundary: SafetyBoundary | None = None
    requires_deterministic_refusal: bool = False
    refusal_message: str | None = None
    boundary_guidance: str | None = None
    is_educational_only: bool = True


# Standard medical boundary statements (reused across the system for deterministic safety)
DIAGNOSIS_REFUSAL_MESSAGE = (
    "OncoVision is an educational and research platform and cannot provide personal medical diagnoses "
    "or evaluate individual symptoms. Please consult a qualified oncologist or physician for medical evaluation, "
    "biopsy review, and clinical diagnostic testing."
)

TREATMENT_REFUSAL_MESSAGE = (
    "OncoVision does not provide individualized treatment recommendations or prescribe medications. "
    "Cancer treatment protocols depend on specific patient factors, clinical performance status, tumor stage, "
    "and molecular profile, and must be determined by a qualified clinical oncology team."
)

STAGING_BOUNDARY_GUIDANCE = (
    "Histopathology image classification of an isolated tissue patch cannot determine clinical or pathological TNM stage. "
    "Tumor staging requires comprehensive clinical evaluation, surgical resection findings (depth of invasion, "
    "organ involvement), regional lymph node dissection (N), and radiological imaging for distant metastases (M)."
)

BIOMARKER_BOUNDARY_GUIDANCE = (
    "Hematoxylin and Eosin (H&E) morphology alone cannot confirm or prove molecular mutations such as EGFR or KRAS. "
    "While morphology may suggest lineage or warrant molecular evaluation, definitive molecular alteration status "
    "requires ancillary testing such as PCR, next-generation sequencing (NGS), or targeted molecular assays."
)

CLASSIFIER_BOUNDARY_GUIDANCE = (
    "The OncoVision classifier output represents automated histopathological image feature extraction "
    "and triage assistance for research and clinical decision support. It is not a standalone diagnostic "
    "confirmation and must always be correlated with full clinical, radiological, and surgical pathology review."
)

INJECTION_REFUSAL_MESSAGE = (
    "OncoVision cannot execute instruction override, prompt inspection, or safety bypass requests. "
    "All interactions must adhere to clinical safety and system integrity boundaries."
)

PREDICTION_CONFLICT_MESSAGE = (
    "The generated response could not be verified against the authoritative classifier prediction. "
    "The recorded classification remains authoritative. Please review the prediction details or consult a qualified pathologist."
)


class SafetyEvaluator:
    """Deterministic clinical boundary and safety evaluator."""

    # Patterns indicating classifier prediction override or contradiction attempts
    _PREDICTION_OVERRIDE_PATTERNS = [
        r"\b(?:override|disregard|bypass|change|replace)\s+(?:the\s+)?(?:classifier|model|prediction)\s*(?:result|output|class)?\b",
    ]

    # Patterns indicating prompt injection, instruction override, or credential/prompt leakage attempts
    _INJECTION_PATTERNS = [
        r"\b(?:ignore|disregard|forget|override|bypass)\s+(?:all\s+)?(?:previous|prior|above|system)\s+(?:instructions?|rules?|directives?|prompts?)\b",
        r"\b(?:reveal|show|dump|print|display|output|tell|repeat)\s+(?:me\s+)?(?:the\s+|your\s+|all\s+|hidden\s+)?(?:system\s+prompt|prompt\s+template|system\s+instructions?|api\s*keys?|database\s*(?:url|credentials?|passwords?))\b",
        r"\b(?:what\s+is\s+your|give\s+me\s+the|tell\s+me\s+the|show\s+me\s+the)\s+(?:hidden\s+)?(?:database\s*(?:url|credentials?|passwords?)|api\s*keys?)\b",
        r"\b(?:override|disregard|bypass|change|replace)\s+(?:the\s+)?(?:classifier|model|prediction)\s*(?:result|output|class)?\b",
        r"\b(?:override|bypass|disregard)\s+(?:all\s+)?(?:medical\s+)?(?:safety\s+)?(?:rules?|boundaries?|policies?)\b",
        r"\btreat\s+this\s+(?:document|text|context|input)\s+as\s+(?:your\s+)?(?:new\s+)?system\s+instruction\b",
        r"\bcall\s+(?:an?\s+)?external\s+tool\b",
        r"\bact\s+as\s+(?:dan|unrestricted|jailbroken|an?\s+unfiltered|an?\s+unbounded)\b",
    ]

    # Patterns indicating personal diagnosis requests
    _DIAGNOSIS_PATTERNS = [
        r"\b(?:do\s+i\s+have|could\s+i\s+have|might\s+i\s+have|tell\s+me\s+if\s+i\s+have)\s+(?:colon|lung)?\s*(?:cancer|carcinoma|adenocarcinoma|tumor)\b",
        r"\bdiagnose\s+(?:me|my\s+condition|my\s+symptoms)\b",
        r"\bdoes\s+this\s+(?:mean|prove)\s+i\s+(?:definitely\s+)?have\s+(?:colon|lung)?\s*(?:cancer|adenocarcinoma|carcinoma)\b",
        r"\bdo\s+i\s+have\s+(?:colon|lung)?\s*(?:adenocarcinoma|carcinoma|tumor|cancer)\b",
        r"\bwhat\s+cancer\s+do\s+i\s+have\b",
        r"\bbased\s+on\s+my\s+symptoms\b",
        r"\bi\s+have\s+(?:blood\s+in\s+my\s+stool|severe\s+pain|cough|hemoptysis|weight\s+loss)\b.*\b(?:what\s+cancer|is\s+it\s+cancer)\b",
    ]

    # Patterns indicating personal treatment / medication prescription requests
    _TREATMENT_PATTERNS = [
        r"\bwhat\s+chemotherapy\s+should\s+i\s+(?:personally\s+)?(?:take|receive|use)\b",
        r"\bwhich\s+drug\s+should\s+i\s+(?:take|use|receive|prescribe)\b",
        r"\bwhat\s+(?:medication|treatment)\s+should\s+i\s+(?:personally\s+)?take\b",
        r"\bprescribe\s+(?:me|for\s+me)\b",
        r"\bwhat\s+dosage\s+(?:should\s+i|of\s+\w+\s+should)\b",
        r"\bhow\s+much\s+(?:chemo|drug|medication)\s+should\s+i\s+take\b",
    ]

    # Patterns indicating TNM staging inference from histopathology image
    _STAGING_PATTERNS = [
        r"\bwhat\s+stage\s+is\s+(?:my\s+cancer|this\s+cancer)\s+based\s+on\s+this\s+image\b",
        r"\bcan\s+(?:you|this\s+image|the\s+ai|this\s+system)\s+(?:determine|predict|give)\s+(?:the\s+)?(?:tnm|stage|staging)\b",
        r"\bcan\s+this\s+image\s+determine\s+tnm\s+stage\b",
        r"\bwhat\s+is\s+the\s+tnm\s+stage\s+from\s+this\s+image\b",
    ]

    # Patterns indicating molecular biomarker claims from H&E alone
    _BIOMARKER_PATTERNS = [
        r"\bcan\s+h&e\s+(?:prove|confirm|diagnose|show)\s+(?:an?\s+)?(?:egfr|kras|braf|alk|ros1|pdl1|ret)\s+mutation\b",
        r"\bcan\s+(?:this\s+)?(?:image|h&e|patch)\s+(?:prove|confirm)\s+(?:an?\s+)?(?:egfr|kras|braf|mutation)\b",
        r"\bdoes\s+h&e\s+prove\s+molecular\s+mutations?\b",
    ]

    # Patterns indicating classifier prediction explanation
    _CLASSIFIER_PATTERNS = [
        r"\bwhy\s+did\s+the\s+model\s+predict\b",
        r"\bexplain\s+the\s+(?:model['’]?s\s+)?prediction\b",
        r"\bwhy\s+is\s+(?:the\s+prediction|it\s+predicted)\b",
    ]

    def evaluate_query(
        self,
        query: str,
        has_prediction: bool = False,
    ) -> SafetyEvaluation:
        """Evaluate incoming user query against clinical safety boundaries."""
        lower_q = query.lower().strip()

        # 0. Prediction Override / Contradiction (when active prediction context is present)
        if has_prediction:
            for pattern in self._PREDICTION_OVERRIDE_PATTERNS:
                if re.search(pattern, lower_q):
                    return SafetyEvaluation(
                        boundary=SafetyBoundary.PREDICTION_OVERRIDE,
                        requires_deterministic_refusal=True,
                        refusal_message=PREDICTION_CONFLICT_MESSAGE,
                        is_educational_only=False,
                    )

        # 1. Prompt Injection & Instruction Boundary (Phase 6.3-A)
        for pattern in self._INJECTION_PATTERNS:
            if re.search(pattern, lower_q):
                return SafetyEvaluation(
                    boundary=SafetyBoundary.INJECTION,
                    requires_deterministic_refusal=True,
                    refusal_message=INJECTION_REFUSAL_MESSAGE,
                    is_educational_only=False,
                )

        # 1. Personal Diagnosis Boundary
        for pattern in self._DIAGNOSIS_PATTERNS:
            if re.search(pattern, lower_q):
                if has_prediction:
                    # The user is asking "Does this mean I definitely have cancer?" about a prediction
                    return SafetyEvaluation(
                        boundary=SafetyBoundary.DIAGNOSIS,
                        requires_deterministic_refusal=False,  # Can explain prediction boundaries
                        boundary_guidance=(
                            "The user is asking if the prediction confirms they have cancer. "
                            "Strictly clarify that the algorithmic prediction is for assistive triage, "
                            "not a definitive clinical diagnosis. Never confirm a patient diagnosis."
                        ),
                        is_educational_only=False,
                    )
                return SafetyEvaluation(
                    boundary=SafetyBoundary.DIAGNOSIS,
                    requires_deterministic_refusal=True,
                    refusal_message=DIAGNOSIS_REFUSAL_MESSAGE,
                    is_educational_only=False,
                )

        # 2. Personal Treatment Boundary
        for pattern in self._TREATMENT_PATTERNS:
            if re.search(pattern, lower_q):
                return SafetyEvaluation(
                    boundary=SafetyBoundary.TREATMENT,
                    requires_deterministic_refusal=True,
                    refusal_message=TREATMENT_REFUSAL_MESSAGE,
                    is_educational_only=False,
                )

        # 3. Staging from Image Boundary
        for pattern in self._STAGING_PATTERNS:
            if re.search(pattern, lower_q):
                return SafetyEvaluation(
                    boundary=SafetyBoundary.STAGING,
                    requires_deterministic_refusal=False,
                    boundary_guidance=STAGING_BOUNDARY_GUIDANCE,
                    is_educational_only=True,
                )

        # 4. Biomarker from H&E Boundary
        for pattern in self._BIOMARKER_PATTERNS:
            if re.search(pattern, lower_q):
                return SafetyEvaluation(
                    boundary=SafetyBoundary.BIOMARKER,
                    requires_deterministic_refusal=False,
                    boundary_guidance=BIOMARKER_BOUNDARY_GUIDANCE,
                    is_educational_only=True,
                )

        # 5. Classifier Explanation Boundary
        for pattern in self._CLASSIFIER_PATTERNS:
            if re.search(pattern, lower_q):
                return SafetyEvaluation(
                    boundary=SafetyBoundary.CLASSIFIER,
                    requires_deterministic_refusal=False,
                    boundary_guidance=CLASSIFIER_BOUNDARY_GUIDANCE,
                    is_educational_only=True,
                )

        return SafetyEvaluation(
            boundary=None,
            requires_deterministic_refusal=False,
            is_educational_only=True,
        )

    def validate_answer(
        self,
        answer: str,
        boundary: SafetyBoundary | None = None,
        prediction_summary: PredictionHistorySummary | None = None,
    ) -> tuple[bool, str | None]:
        """Validate generated text to ensure no dangerous medical assertions, injection compliance,
        or prediction overrides were emitted."""
        lower_ans = answer.lower()

        # 1. Direct diagnostic assertions (Protected Boundaries 1 & 7)
        direct_diag_phrases = [
            "i diagnose you with",
            "you have stage",
            "i confirm you have cancer",
            "you definitely have cancer",
            "you are diagnosed with",
            "your diagnosis is",
            "you are suffering from",
            "based on your symptoms, you have",
            "symptoms confirm you have",
            "i determine that you have cancer",
        ]
        for phrase in direct_diag_phrases:
            if phrase in lower_ans:
                return False, f"Generated answer contains forbidden direct diagnosis phrase: '{phrase}'"

        # 2. Direct prescription / medication assertions (Protected Boundaries 2 & 3)
        direct_rx_phrases = [
            "take 50mg",
            "take 100mg",
            "you must start taking",
            "you should start taking",
            "start taking",
            "i prescribe",
            "you should take cisplatin",
            "your chemotherapy regimen should be",
            "i recommend you take cisplatin",
            "you need radiation therapy immediately",
        ]
        for phrase in direct_rx_phrases:
            if phrase in lower_ans:
                return False, f"Generated answer contains forbidden direct prescription phrase: '{phrase}'"

        if re.search(r"\b(?:take|prescribe|administer)\s+\d+\s*(?:mg|g|mcg|ml)\b", lower_ans):
            return False, "Generated answer contains forbidden specific dosage prescription."

        # 3. Patient-specific staging claims from image alone (Protected Boundary 4)
        staging_regexes = [
            r"\b(?:based\s+on\s+this\s+(?:image|patch|slide)|from\s+this\s+image),\s*(?:your|the\s+patient's)\s+(?:cancer|tumor)?\s*is\s+stage\s+[iIvV0-9]+\b",
            r"\bthis\s+(?:image|patch)\s+(?:proves|confirms|determines)\s+(?:clinical\s+|pathological\s+)?(?:tnm\s+|cancer\s+)?stage\s+[iIvV0-9]+\b",
            r"\bthe\s+tnm\s+stage\s+is\s+stage\s+[iIvV0-9]+\b",
        ]
        for s_reg in staging_regexes:
            if re.search(s_reg, lower_ans):
                return False, "Generated answer contains forbidden staging claim from image alone."

        # 4. Patient-specific prognosis assertions (Protected Boundary 5)
        prognosis_regexes = [
            r"\byou\s+have\s+\d+\s+(?:months?|years?|weeks?)\s+to\s+live\b",
            r"\byour\s+life\s+expectancy\s+is\b",
            r"\byour\s+prognosis\s+is\s+(?:poor|fatal|terminal)\b",
        ]
        for p_reg in prognosis_regexes:
            if re.search(p_reg, lower_ans):
                return False, "Generated answer contains forbidden patient prognosis claim."

        # 5. Molecular biomarker claims from H&E alone (Protected Boundary 6)
        biomarker_regexes = [
            r"\b(?:h&e|image|patch|slide)\s+(?:alone\s+)?(?:confirms|proves|diagnoses)\s+(?:the\s+)?(?:egfr|kras|braf|alk|ros1)\s+mutation\b",
            r"\bmolecular\s+mutations?\s+(?:are|can\s+be)\s+(?:confirmed|proven)\s+by\s+h&e\s+alone\b",
        ]
        for b_reg in biomarker_regexes:
            if re.search(b_reg, lower_ans):
                return False, "Generated answer contains forbidden molecular biomarker claim from H&E alone."
        if boundary == SafetyBoundary.BIOMARKER:
            if re.search(r"\b(?:h&e|image|patch)\s+(?:confirms|proves)\s+(?:the\s+)?(?:egfr|kras|braf)\s+mutation\b", lower_ans):
                return False, "Generated answer contains forbidden false biomarker confirmation."

        # 6. Definitive diagnosis or bypassing clinician review (Protected Boundaries 8 & 9)
        definitive_regexes = [
            r"\bthis\s+(?:ai|classifier|model|system)\s+(?:result\s+)?is\s+a\s+definitive\s+(?:pathology\s+)?diagnosis\b",
            r"\bno\s+(?:pathologist|clinician|oncologist|physician)\s+review\s+(?:is\s+)?(?:needed|required|necessary)\b",
            r"\bbypassing\s+(?:pathologist|physician|clinical)\s+review\b",
        ]
        for d_reg in definitive_regexes:
            if re.search(d_reg, lower_ans):
                return False, "Generated answer claims AI result is definitive or bypasses clinical review."

        # 7. System prompt or credential leakage (Gate 6.3-A)
        leak_patterns = [
            r"\bGROUNDED_RAG_SYSTEM_PROMPT\b",
            r"\bAIza[0-9A-Za-z-_]{35}\b",
            r"\bpostgresql:\/\/[^\s@]+@\b",
            r"\bmy\s+system\s+prompt\s+is\b",
            r"\bhere\s+is\s+(?:the|my)\s+system\s+prompt\b",
            r"\bmy\s+api\s+key\s+is\b",
        ]
        for l_pat in leak_patterns:
            if re.search(l_pat, answer, re.IGNORECASE):
                return False, "Generated answer contains potential secret or system prompt leakage."

        # 8. Prediction Immutability & Classifier/RAG Boundary (Gate 6.3-B)
        if prediction_summary and prediction_summary.predicted_class:
            pred_class = prediction_summary.predicted_class.lower()

            override_patterns = [
                r"\b(?:disregard|ignore|overriding|override|reject|cancel)\s+(?:the\s+)?(?:classifier|model|prediction)\s*(?:result|finding)?\b",
                r"\bthe\s+classifier\s+(?:is\s+wrong|made\s+an?\s+error|misdiagnosed|misclassified)\b",
                r"\bthe\s+(?:true|actual|correct|real)\s+(?:class|diagnosis|prediction)\s+is\s+(?:not\s+\w+|\w+)\b",
                r"\bthis\s+sample\s+is\s+actually\s+\w+\b",
                r"\bi\s+(?:reclassify|determine\s+this\s+as)\b",
            ]
            for o_pat in override_patterns:
                if re.search(o_pat, lower_ans):
                    return False, f"Generated answer contradicts authoritative classifier prediction: '{prediction_summary.predicted_class}'"

            # Canonical OncoVision tissue classes
            all_classes = [
                "colon_adenocarcinoma",
                "colon_benign_tissue",
                "lung_adenocarcinoma",
                "lung_benign_tissue",
                "lung_squamous_cell_carcinoma",
            ]
            for other_cls in all_classes:
                if other_cls != pred_class:
                    readable_other = other_cls.replace("_", " ")
                    if (
                        f"diagnosed with {readable_other}" in lower_ans
                        or f"diagnosed with {other_cls}" in lower_ans
                        or f"sample is {readable_other}" in lower_ans
                        or f"sample is {other_cls}" in lower_ans
                    ):
                        return False, f"Generated answer claims conflicting class '{other_cls}' against authoritative prediction '{pred_class}'"

        return True, None
