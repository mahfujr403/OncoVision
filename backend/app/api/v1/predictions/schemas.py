"""Prediction API request schemas (Phase 4.3 - ADR-012).

Defines the public request contract for `POST /api/v1/predictions`.

The uploaded histopathology image travels as a `multipart/form-data` file
part and is accepted by the router directly via FastAPI's `UploadFile`
(see `app.api.v1.predictions.router`); it is intentionally never modeled
as a Pydantic field here, since Pydantic models do not represent
multipart file parts.

`PredictionRequestSchema` describes only the optional control flags a
caller may submit alongside that file. `as_form` adapts those fields into
individual `Form(...)` parameters so the flags are validated by FastAPI
and documented in OpenAPI/Swagger as part of the same multipart request,
without requiring the router to duplicate field defaults or constraints.

This module defines the CONTRACT only. It must never contain AI Runtime
calls, Prediction Engine calls, Ensemble logic, history persistence, or
report generation -- see Backend Progress, Phase 4.4 onward.
"""

from typing import Annotated, Any

from fastapi import Form
from pydantic import BaseModel, ConfigDict, Field

DEFAULT_CONFIDENCE_THRESHOLD: float = 0.5


class PredictionRequestSchema(BaseModel):
    """Optional control flags accepted alongside an image upload.

    All fields are optional and carry production-safe defaults, so a
    caller may submit only the image with no accompanying flags.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "confidence_threshold": 0.5,
                "include_individual_predictions": True,
                "include_runtime_statistics": False,
                "save_history": True,
                "generate_report": False,
                "future_metadata": None,
            }
        }
    )

    confidence_threshold: float = Field(
        default=DEFAULT_CONFIDENCE_THRESHOLD,
        ge=0.0,
        le=1.0,
        description=(
            "Minimum confidence required for a prediction to be treated as "
            "reliable. Used only for downstream flagging/formatting; it "
            "never alters model inference itself."
        ),
    )
    include_individual_predictions: bool = Field(
        default=True,
        description="Whether the response should include the per-model prediction breakdown.",
    )
    include_runtime_statistics: bool = Field(
        default=False,
        description="Whether the response should include AI Runtime health/statistics.",
    )
    save_history: bool = Field(
        default=True,
        description=(
            "Whether this prediction should be persisted to prediction history "
            "(Phase 5). Accepted now for API contract stability; not yet acted on."
        ),
    )
    generate_report: bool = Field(
        default=False,
        description=(
            "Whether a downloadable prediction report should be generated "
            "(Phase 6). Accepted now for API contract stability; not yet acted on."
        ),
    )
    future_metadata: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Reserved extension point for forward-compatible request metadata. "
            "Not consumed by the current API version and not exposed as a form "
            "field; available for future JSON-bodied prediction endpoints."
        ),
    )

    @classmethod
    def as_form(
        cls,
        confidence_threshold: Annotated[
            float,
            Form(
                description=(
                    "Minimum confidence required for a prediction to be "
                    "treated as reliable (0.0-1.0)."
                ),
                ge=0.0,
                le=1.0,
            ),
        ] = DEFAULT_CONFIDENCE_THRESHOLD,
        include_individual_predictions: Annotated[
            bool,
            Form(description="Include the per-model prediction breakdown in the response."),
        ] = True,
        include_runtime_statistics: Annotated[
            bool,
            Form(description="Include AI Runtime health/statistics in the response."),
        ] = False,
        save_history: Annotated[
            bool,
            Form(description="Persist this prediction to prediction history (Phase 5)."),
        ] = True,
        generate_report: Annotated[
            bool,
            Form(description="Generate a downloadable prediction report (Phase 6)."),
        ] = False,
    ) -> "PredictionRequestSchema":
        """Build a `PredictionRequestSchema` from individual multipart form fields.

        Used as a FastAPI dependency (`Depends(PredictionRequestSchema.as_form)`)
        so the router receives one validated object instead of five loose
        parameters. `future_metadata` is intentionally excluded here: it is a
        reserved extension point for future JSON-bodied endpoints, not a
        practical multipart form field.
        """
        return cls(
            confidence_threshold=confidence_threshold,
            include_individual_predictions=include_individual_predictions,
            include_runtime_statistics=include_runtime_statistics,
            save_history=save_history,
            generate_report=generate_report,
        )
