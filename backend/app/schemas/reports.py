"""Reporting API response schemas (Phase 6.5, ADR-041).

Defines the public response contract for the Reporting Router
(`app.api.v1.reports`):

- `GET /api/v1/reports/analytics`  -> `PredictionAnalyticsResponseSchema`
- `GET /api/v1/reports/export/csv` -> a raw, streamed `text/csv` file
  (no JSON schema; see `app.api.v1.reports`)
- `GET /api/v1/reports/export/pdf` -> a raw, streamed `application/pdf`
  file (no JSON schema; see `app.api.v1.reports`)

These schemas represent the EXTERNAL API only and are intentionally kept
independent from the internal domain models they project --
`app.reports.analytics.analytics_result.PredictionAnalyticsResult`
(ADR-038) -- mirroring the same internal/external separation already
established between `app.history.prediction_history.PredictionHistory`
and `app.api.v1.history.responses` (ADR-034).

Every field on `PredictionAnalyticsResponseSchema` is copied directly
from the already-computed `PredictionAnalyticsResult`; this module
performs no calculation, recalculation, or aggregation of its own.
`PredictionAnalyticsService` (Phase 6.2, ADR-038) remains the single
source of truth for every analytics figure.
"""

from pydantic import BaseModel, ConfigDict, Field

from app.reports.analytics.analytics_result import PredictionAnalyticsResult

__all__ = ["PredictionAnalyticsResponseSchema"]


class PredictionAnalyticsResponseSchema(BaseModel):
    """Complete public response payload for the Prediction Analytics endpoint.

    A public projection of
    `app.reports.analytics.analytics_result.PredictionAnalyticsResult`
    (ADR-038) -- every field is copied directly from the domain object
    via `from_domain()`; this schema performs no calculation of its own.
    Carried as the `data` field of the application's global `APIResponse`
    envelope (`app.schemas.response.APIResponse`) -- never returned
    standalone.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "analytics_id": "a1b2c3d4-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
                "generated_at": "2026-07-27T10:00:00+00:00",
                "total_predictions": 42,
                "successful_predictions": 40,
                "failed_predictions": 2,
                "success_rate": 95.24,
                "average_confidence": 91.35,
                "average_agreement_ratio": 0.93,
                "most_predicted_class": "lung_aca",
                "class_distribution": {"lung_aca": 22, "lung_scc": 12, "lung_n": 6},
                "confidence_distribution": {"60-80": 4, "80-100": 36},
                "first_prediction_date": "2026-06-01T08:15:00+00:00",
                "latest_prediction_date": "2026-07-27T10:00:00+00:00",
                "predictions_today": 3,
                "predictions_this_week": 11,
                "predictions_this_month": 42,
            }
        }
    )

    analytics_id: str = Field(description="Unique identifier for this analytics computation run.")
    generated_at: str = Field(
        description="ISO 8601 timestamp of when this analytics computation was generated."
    )
    total_predictions: int = Field(
        description="Total number of the authenticated user's prediction history records considered."
    )
    successful_predictions: int = Field(
        description="Number of considered history records with a final predicted class."
    )
    failed_predictions: int = Field(
        description="Number of considered history records with no final predicted class."
    )
    success_rate: float = Field(
        ge=0.0,
        le=100.0,
        description="Percentage (0-100) of `total_predictions` that were successful.",
    )
    average_confidence: float = Field(
        ge=0.0,
        le=100.0,
        description="Mean final prediction confidence percentage across successful records.",
    )
    average_agreement_ratio: float = Field(
        ge=0.0,
        le=1.0,
        description="Mean ensemble agreement ratio across successful records.",
    )
    most_predicted_class: str | None = Field(
        default=None,
        description="The predicted class label appearing most often. Null when no record succeeded.",
    )
    class_distribution: dict[str, int] = Field(
        default_factory=dict,
        description="Count of considered history records per predicted class label.",
    )
    confidence_distribution: dict[str, int] = Field(
        default_factory=dict,
        description=(
            "Count of considered history records per fixed final-confidence "
            "percentage bucket ('0-20', '20-40', '40-60', '60-80', '80-100')."
        ),
    )
    first_prediction_date: str | None = Field(
        default=None, description="ISO 8601 timestamp of the oldest record considered."
    )
    latest_prediction_date: str | None = Field(
        default=None, description="ISO 8601 timestamp of the newest record considered."
    )
    predictions_today: int = Field(
        description="Number of history records created since the start of the current UTC day."
    )
    predictions_this_week: int = Field(
        description="Number of history records created since the start of the current ISO week."
    )
    predictions_this_month: int = Field(
        description="Number of history records created since the start of the current UTC month."
    )

    @classmethod
    def from_domain(cls, result: PredictionAnalyticsResult) -> "PredictionAnalyticsResponseSchema":
        """Project an internal `PredictionAnalyticsResult` onto its public response contract."""
        return cls(
            analytics_id=result.analytics_id,
            generated_at=result.generated_at,
            total_predictions=result.total_predictions,
            successful_predictions=result.successful_predictions,
            failed_predictions=result.failed_predictions,
            success_rate=result.success_rate,
            average_confidence=result.average_confidence,
            average_agreement_ratio=result.average_agreement_ratio,
            most_predicted_class=result.most_predicted_class,
            class_distribution=result.class_distribution,
            confidence_distribution=result.confidence_distribution,
            first_prediction_date=result.first_prediction_date,
            latest_prediction_date=result.latest_prediction_date,
            predictions_today=result.predictions_today,
            predictions_this_week=result.predictions_this_week,
            predictions_this_month=result.predictions_this_month,
        )
