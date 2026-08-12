"""Prediction History API response schemas (Phase 5.3/5.4/5.5 - ADR-034/ADR-035).

Defines the public response contract for `GET /api/v1/predictions/history`
and `GET /api/v1/predictions/history/{history_id}`.

These schemas represent the EXTERNAL API only and are intentionally kept
independent from the Prediction API's own response contract
(`app.api.v1.predictions.responses`, ADR-012): the two APIs are allowed to
evolve on separate timelines, and Prediction History is not permitted to
depend on, or be depended on by, the Prediction API's public shapes.

Every field here is copied directly from the already-computed
`app.history.prediction_history.PredictionHistory` domain object (ADR-032)
-- this module performs no calculation, recalculation, or inference of its
own.

Phase 5.4 (ADR-035) adds `PredictionHistoryPaginationSchema`, a direct
public projection of `app.history.pagination.PredictionHistoryPageMetadata`,
and makes it a required part of `PredictionHistoryListResponseSchema` --
every field is copied verbatim from the already-computed
`PredictionHistoryPageMetadata`; this module still performs no pagination
arithmetic of its own.

Phase 5.5 (History Detail Retrieval, ADR-035 update) adds
`PredictionHistoryImageMetadataSchema`, `PredictionHistoryRuntimeInfoSchema`,
and `PredictionHistoryDetailResponseSchema`. Unlike
`PredictionHistoryItemSchema` (the summarized list-response projection),
the detail schema additionally exposes the full
`app.history.metadata.PredictionHistoryMetadata` snapshot -- uploaded
image metadata and runtime information -- for a single record. Every
field is still copied directly from the already-computed
`PredictionHistory` domain object; this module performs no calculation
of its own here either.
"""

from pydantic import BaseModel, ConfigDict, Field

from app.history.enums import PredictionHistoryStatus

__all__ = [
    "PredictionHistoryStatus",
    "PredictionHistoryModelEntrySchema",
    "PredictionHistoryItemSchema",
    "PredictionHistoryPaginationSchema",
    "PredictionHistoryListResponseSchema",
    "PredictionHistoryImageMetadataSchema",
    "PredictionHistoryRuntimeInfoSchema",
    "PredictionHistoryDetailResponseSchema",
]


class PredictionHistoryModelEntrySchema(BaseModel):
    """Simplified per-model prediction result exposed to API clients.

    A public projection of `app.history.summary.PredictionHistoryModelEntry`,
    itself already a simplified projection of
    `app.ml.prediction.prediction_result.IndividualPrediction` (ADR-032).
    """

    model_name: str = Field(description="Human-readable display name of the model.")
    prediction: str = Field(description="This model's own predicted class label.")
    confidence: float = Field(
        ge=0.0,
        le=100.0,
        description="This model's own top-class confidence, as a percentage (0-100).",
    )
    inference_time_ms: float = Field(
        description="Time spent running inference for this model, in milliseconds."
    )


class PredictionHistoryItemSchema(BaseModel):
    """A single stored prediction history record exposed to API clients.

    A public projection of `app.history.prediction_history.PredictionHistory`
    (ADR-032) -- every field is copied directly from the domain object;
    this schema performs no calculation of its own.
    """

    history_id: str = Field(description="Unique identifier of this history record.")
    request_id: str = Field(
        description="Identifier of the original prediction request this record describes."
    )
    status: PredictionHistoryStatus = Field(
        description="Outcome of the prediction pipeline run this record describes."
    )
    created_at: str = Field(
        description="ISO 8601 timestamp of when this history record was created."
    )
    image_filename: str = Field(description="Original filename of the uploaded image.")
    predicted_class: str | None = Field(
        default=None,
        description="Final predicted class label. Null when no winning class was produced.",
    )
    confidence: float = Field(
        ge=0.0,
        le=100.0,
        description="Final prediction confidence, as a percentage (0-100).",
    )
    agreement_ratio: float = Field(
        ge=0.0,
        le=1.0,
        description="Proportion of successful models that agree with `predicted_class`.",
    )
    successful_models: list[str] = Field(
        description="Model IDs whose predictions participated in the final prediction."
    )
    failed_models: list[str] = Field(
        description="Model IDs that were attempted but failed to produce a prediction."
    )
    participating_models: int = Field(
        description="Total number of models attempted (successful and failed)."
    )
    individual_predictions: list[PredictionHistoryModelEntrySchema] = Field(
        default_factory=list,
        description="Per-model prediction breakdown recorded for this request.",
    )


class PredictionHistoryPaginationSchema(BaseModel):
    """Pagination metadata for a prediction history list response (Phase 5.4, ADR-035).

    A direct public projection of
    `app.history.pagination.PredictionHistoryPageMetadata` -- every field
    is copied verbatim; this schema performs no pagination arithmetic of
    its own.
    """

    current_page: int = Field(description="The page number this response describes.")
    page_size: int = Field(description="Maximum number of records requested for this page.")
    total_records: int = Field(
        description="Total number of records matching the request, across every page."
    )
    total_pages: int = Field(description="Total number of pages available for this request.")
    has_next: bool = Field(description="Whether a page after `current_page` exists.")
    has_previous: bool = Field(description="Whether a page before `current_page` exists.")


class PredictionHistoryListResponseSchema(BaseModel):
    """Complete public response payload for a prediction history list request.

    Carried as the `data` field of the application's global `APIResponse`
    envelope (`app.schemas.response.APIResponse`) -- never returned
    standalone.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "history_id": "b1f0c6b2-5c1a-4e9e-9c3a-2f6a0e0f9a11",
                        "request_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                        "status": "success",
                        "created_at": "2026-07-19T10:00:00+00:00",
                        "image_filename": "sample_slide.png",
                        "predicted_class": "lung_adenocarcinoma",
                        "confidence": 96.42,
                        "agreement_ratio": 1.0,
                        "successful_models": ["mobilenetv2", "densenet121"],
                        "failed_models": [],
                        "participating_models": 2,
                        "individual_predictions": [
                            {
                                "model_name": "MobileNetV2",
                                "prediction": "lung_adenocarcinoma",
                                "confidence": 95.10,
                                "inference_time_ms": 42.3,
                            },
                            {
                                "model_name": "DenseNet121",
                                "prediction": "lung_adenocarcinoma",
                                "confidence": 97.05,
                                "inference_time_ms": 88.7,
                            },
                        ],
                    }
                ],
                "count": 1,
                "pagination": {
                    "current_page": 1,
                    "page_size": 20,
                    "total_records": 1,
                    "total_pages": 1,
                    "has_next": False,
                    "has_previous": False,
                },
            }
        }
    )

    items: list[PredictionHistoryItemSchema] = Field(
        description="The authenticated user's stored prediction history, newest first."
    )
    count: int = Field(description="Number of history records included in this response.")
    pagination: PredictionHistoryPaginationSchema = Field(
        description="Pagination metadata describing this page relative to the full, "
        "optionally filtered result set (Phase 5.4, ADR-035)."
    )


class PredictionHistoryImageMetadataSchema(BaseModel):
    """Uploaded image metadata for a single history record (Phase 5.5, ADR-035 update).

    A public projection of the image-scoped fields already carried on
    `app.history.metadata.PredictionHistoryMetadata` -- every field is
    copied directly; this schema performs no calculation of its own.
    """

    filename: str = Field(description="Original filename of the uploaded image.")
    content_type: str = Field(description="Declared MIME type of the uploaded image.")
    size_bytes: int = Field(description="Size of the uploaded image, in bytes.")
    width: int = Field(description="Uploaded image width, in pixels.")
    height: int = Field(description="Uploaded image height, in pixels.")


class PredictionHistoryRuntimeInfoSchema(BaseModel):
    """Runtime information for a single history record (Phase 5.5, ADR-035 update).

    A public projection of the runtime-scoped fields already carried on
    `app.history.metadata.PredictionHistoryMetadata` -- every field is
    copied directly; this schema performs no calculation of its own.
    """

    model_manifest_version: str | None = Field(
        default=None,
        description=(
            "Version identifier of the Model Manifest active at prediction "
            "time. Null when unavailable at mapping time."
        ),
    )
    processing_time_ms: float | None = Field(
        default=None,
        description=(
            "Total end-to-end wall-clock time spent handling the original "
            "request, in milliseconds. Null when unavailable at mapping time."
        ),
    )


class PredictionHistoryDetailResponseSchema(BaseModel):
    """Complete public response payload for a single prediction history record.

    A public projection of `app.history.prediction_history.PredictionHistory`
    (ADR-032), extended -- relative to `PredictionHistoryItemSchema` -- with
    the full uploaded image metadata and runtime information for this one
    record (Phase 5.5, ADR-035 update). Carried as the `data` field of the
    application's global `APIResponse` envelope (`app.schemas.response.APIResponse`)
    -- never returned standalone.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "history_id": "b1f0c6b2-5c1a-4e9e-9c3a-2f6a0e0f9a11",
                "request_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                "status": "success",
                "created_at": "2026-07-19T10:00:00+00:00",
                "predicted_class": "lung_adenocarcinoma",
                "confidence": 96.42,
                "agreement_ratio": 1.0,
                "successful_models": ["mobilenetv2", "densenet121"],
                "failed_models": [],
                "participating_models": 2,
                "individual_predictions": [
                    {
                        "model_name": "MobileNetV2",
                        "prediction": "lung_adenocarcinoma",
                        "confidence": 95.10,
                        "inference_time_ms": 42.3,
                    },
                    {
                        "model_name": "DenseNet121",
                        "prediction": "lung_adenocarcinoma",
                        "confidence": 97.05,
                        "inference_time_ms": 88.7,
                    },
                ],
                "image_metadata": {
                    "filename": "sample_slide.png",
                    "content_type": "image/png",
                    "size_bytes": 204800,
                    "width": 224,
                    "height": 224,
                },
                "runtime_info": {
                    "model_manifest_version": "2026.07.1",
                    "processing_time_ms": 154.8,
                },
            }
        }
    )

    history_id: str = Field(description="Unique identifier of this history record.")
    request_id: str = Field(
        description="Identifier of the original prediction request this record describes."
    )
    status: PredictionHistoryStatus = Field(
        description="Outcome of the prediction pipeline run this record describes."
    )
    created_at: str = Field(
        description="ISO 8601 timestamp of when this history record was created."
    )
    predicted_class: str | None = Field(
        default=None,
        description="Final predicted class label. Null when no winning class was produced.",
    )
    confidence: float = Field(
        ge=0.0,
        le=100.0,
        description="Final prediction confidence, as a percentage (0-100).",
    )
    agreement_ratio: float = Field(
        ge=0.0,
        le=1.0,
        description="Proportion of successful models that agree with `predicted_class`.",
    )
    successful_models: list[str] = Field(
        description="Model IDs whose predictions participated in the final prediction."
    )
    failed_models: list[str] = Field(
        description="Model IDs that were attempted but failed to produce a prediction."
    )
    participating_models: int = Field(
        description="Total number of models attempted (successful and failed)."
    )
    individual_predictions: list[PredictionHistoryModelEntrySchema] = Field(
        default_factory=list,
        description="Per-model prediction breakdown recorded for this request.",
    )
    image_metadata: PredictionHistoryImageMetadataSchema = Field(
        description="Metadata of the image that was uploaded for this prediction request."
    )
    runtime_info: PredictionHistoryRuntimeInfoSchema = Field(
        description="Runtime information recorded for this prediction request."
    )
