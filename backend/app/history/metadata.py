"""Prediction History Metadata (Phase 5.1, ADR-032).

`PredictionHistoryMetadata` carries the request-scoped and image-scoped
facts a history record needs to remain self-describing without
recomputation. Every field is copied verbatim from
`app.services.prediction_context.PredictionContext` (already collected
by `PredictionService` during upload validation, Phase 4.2 / ADR-011) --
this module performs no validation or derivation of its own.
"""

from pydantic import BaseModel, ConfigDict, Field


class PredictionHistoryMetadata(BaseModel):
    """Immutable snapshot of request and image metadata for one history record.

    Field-for-field mirror of the relevant `PredictionContext` attributes,
    owned by the history package so it never needs to import
    `PredictionContext` consumers from the API layer.
    """

    model_config = ConfigDict(frozen=True)

    request_id: str = Field(description="Unique identifier of the prediction request.")
    requested_at: str = Field(description="ISO 8601 timestamp of when the request was received.")

    user_id: str = Field(description="Unique identifier of the requesting user.")
    user_email: str = Field(description="Email address of the requesting user.")

    image_filename: str = Field(description="Original filename of the uploaded image.")
    image_content_type: str = Field(description="Declared MIME type of the uploaded image.")
    image_size_bytes: int = Field(description="Size of the uploaded image, in bytes.")
    image_width: int = Field(description="Uploaded image width, in pixels.")
    image_height: int = Field(description="Uploaded image height, in pixels.")

    model_manifest_version: str | None = Field(
        default=None,
        description=(
            "Version identifier of the Model Manifest active at prediction "
            "time, copied from `RuntimeMetadata.manifest_version` (ADR-016). "
            "None when the RUNTIME pipeline stage did not complete."
        ),
    )
    processing_time_ms: float | None = Field(
        default=None,
        description=(
            "Total end-to-end wall-clock time spent handling the original "
            "request, in milliseconds. None when unavailable at mapping time."
        ),
    )
