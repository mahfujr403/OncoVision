"""Prediction pipeline context (Phase 4.4 - ADR-013).

`PredictionContext` is the single, strongly typed object passed through
every stage of the prediction pipeline (image preprocessing, AI Runtime
Manager, Prediction Engine, Adaptive Ensemble Engine, response building,
history, and reporting). It is built once per request by
`PredictionService` from centralized upload validation output
(`app.core.upload.UploadValidationResult`, ADR-011), the authenticated
user, and the validated request options, and is never reconstructed
mid-pipeline.

`PredictionOptions` is a service-owned projection of
`app.api.v1.predictions.schemas.PredictionRequestSchema` (ADR-012).
`PredictionService` intentionally never imports that API-layer schema
module directly: `app.api.v1.predictions.__init__` re-exports `router`,
which depends on `app.dependencies.services`, which depends on
`app.services.prediction_service` -- importing the schema from the
service layer would close that import cycle. The Prediction Router is
responsible for converting a validated `PredictionRequestSchema` into a
`PredictionOptions` (see `PredictionOptions.from_request`) before calling
`PredictionService.predict()`.

This module defines the CONTEXT shape only. Later phases add fields as
new stages require request-scoped state; they do not replace this object
with something new (see Backend Progress, Phase 4.5 onward).
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.upload import UploadValidationResult


class PredictionOptions(BaseModel):
    """Service-layer projection of the validated prediction request options.

    Field-for-field mirror of `PredictionRequestSchema`'s control flags,
    owned by the service layer so `PredictionService` stays independent
    from the API-layer schema module (see module docstring).
    """

    model_config = ConfigDict(frozen=True)

    confidence_threshold: float = Field(
        description="Minimum confidence required for a prediction to be treated as reliable."
    )
    include_individual_predictions: bool = Field(
        description="Whether the response should include the per-model prediction breakdown."
    )
    include_runtime_statistics: bool = Field(
        description="Whether the response should include AI Runtime health/statistics."
    )
    save_history: bool = Field(
        description="Whether this prediction should be persisted to prediction history (Phase 5)."
    )
    generate_report: bool = Field(
        description="Whether a downloadable prediction report should be generated (Phase 6)."
    )

    @classmethod
    def from_request(cls, request_options: Any) -> "PredictionOptions":
        """Build a `PredictionOptions` from any object exposing the same fields.

        Accepts `PredictionRequestSchema` (or any duck-typed equivalent)
        without importing its module, by reading it through
        `model_dump()` when available and falling back to plain
        attribute access otherwise.

        Args:
            request_options: A validated `PredictionRequestSchema` instance.
        """
        if hasattr(request_options, "model_dump"):
            data = request_options.model_dump()
        else:
            data = {field: getattr(request_options, field) for field in cls.model_fields}
        return cls(**data)


class PredictionContext(BaseModel):
    """Immutable, request-scoped state threaded through the prediction pipeline."""

    model_config = ConfigDict(frozen=True)

    request_id: str = Field(description="Unique identifier for this prediction request.")
    requested_at: str = Field(description="ISO 8601 timestamp of when this request was received.")

    user_id: str = Field(description="Unique identifier of the requesting user.")
    user_email: str = Field(description="Email address of the requesting user.")

    image_filename: str = Field(description="Original filename of the uploaded image.")
    image_content_type: str = Field(description="Declared MIME type of the uploaded image.")
    image_size_bytes: int = Field(description="Size of the uploaded image, in bytes.")
    image_width: int = Field(description="Uploaded image width, in pixels.")
    image_height: int = Field(description="Uploaded image height, in pixels.")

    options: PredictionOptions = Field(
        description="Validated prediction control flags submitted with this request."
    )

    @classmethod
    def from_validated_upload(
        cls,
        request_id: str,
        requested_at: str,
        user_id: str,
        user_email: str,
        validation: UploadValidationResult,
        options: PredictionOptions,
    ) -> "PredictionContext":
        """Build a `PredictionContext` from centralized upload validation output.

        Args:
            request_id: Unique identifier generated for this request.
            requested_at: ISO 8601 timestamp of when the request was received.
            user_id: Unique identifier of the requesting user.
            user_email: Email address of the requesting user.
            validation: Trusted upload metadata from `UploadValidator.validate()`.
            options: Validated prediction control flags for this request.
        """
        return cls(
            request_id=request_id,
            requested_at=requested_at,
            user_id=user_id,
            user_email=user_email,
            image_filename=validation.original_filename,
            image_content_type=validation.content_type,
            image_size_bytes=validation.file_size,
            image_width=validation.width,
            image_height=validation.height,
            options=options,
        )
