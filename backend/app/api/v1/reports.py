"""Reporting API endpoints (Phase 6.5, ADR-041).

Routers only receive requests and delegate to services; no business
logic lives here, matching the convention already established by
`app.api.v1.history.router` and `app.api.v1.predictions.router`
(ADR-010).

This router exposes three read-only, authenticated endpoints over the
Reporting subsystem completed in Phase 6.1-6.4:

- `GET /api/v1/reports/analytics`   -> `PredictionAnalyticsService`
  (Phase 6.2, ADR-038), returned as the standard `APIResponse` JSON
  envelope via `PredictionAnalyticsResponseSchema`.
- `GET /api/v1/reports/export/csv`  -> `CSVExportService` (Phase 6.3,
  ADR-039), streamed back as a raw `text/csv` download -- *not* wrapped
  in the `APIResponse` envelope, since the response body itself must be
  the downloadable file.
- `GET /api/v1/reports/export/pdf`  -> `PDFExportService` (Phase 6.4,
  ADR-040), streamed back as a raw `application/pdf` download, for the
  same reason.

Every endpoint is scoped to `current_user.id` exactly the way
`app.api.v1.history.router` already scopes Prediction History retrieval:
ownership is enforced downstream by `PredictionHistoryRepository`
(ADR-032/ADR-034), and this router never queries prediction data itself.
No filtering, pagination, scheduling, email delivery, or admin access is
introduced here (out of scope per this phase's directive) -- each
endpoint always operates over the authenticated user's complete
prediction history, mirroring how `ReportService.generate_report()`
already behaves without an explicit `PredictionHistoryFilter`.

Phase 6.6 Reporting Hardening (ADR-042) makes two changes here, on top of
the services it hardens:

- Every endpoint now documents a `413` response, raised by the service
  layer (`AnalyticsExportLimitExceededError`, `CSVExportLimitExceededError`,
  `PDFExportLimitExceededError`) whenever the authenticated user's
  matching prediction history -- or an already-generated export document
  -- exceeds a configured limit (`Settings.REPORT_EXPORT_MAX_ROWS`/
  `Settings.REPORT_EXPORT_MAX_SIZE_BYTES`). No router-level code raises
  this; it is handled entirely by the existing centralized
  `app.core.exceptions.oncovision_exception_handler`, exactly like every
  other `OncoVisionError` this router already relies on.
- The CSV/PDF export endpoints now stream their already-generated
  `CSVExportResult.content`/`PDFExportResult.content` back to the client
  in fixed-size chunks via `StreamingResponse` instead of returning the
  entire document as a single in-memory `Response` body, avoiding
  holding a second full copy of the document in memory during transfer.
  The bytes returned to the client, `Content-Type`, and
  `Content-Disposition` are unchanged.
"""

from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse

from app.api.v1.predictions.examples import AUTHENTICATION_ERROR_EXAMPLE, INTERNAL_ERROR_EXAMPLE
from app.api.v1.reports_examples import EXPORT_LIMIT_EXCEEDED_EXAMPLE
from app.constants.app import TAG_REPORTS
from app.core.logging import get_logger
from app.dependencies.auth import get_current_active_user
from app.dependencies.services import (
    get_csv_export_service,
    get_pdf_export_service,
    get_prediction_analytics_service,
)
from app.models.user import User
from app.reports.csv.csv_export_service import CSVExportService
from app.reports.pdf.pdf_export_service import PDFExportService
from app.schemas.response import APIResponse
from app.schemas.reports import PredictionAnalyticsResponseSchema
from app.services.prediction_analytics_service import PredictionAnalyticsService
from app.utils.response import success_response

logger = get_logger(__name__)

router = APIRouter(prefix="/reports", tags=[TAG_REPORTS])

#: Fixed download filenames, per this phase's explicit directive -- the
#: `Content-Disposition` header clients see on every export, regardless
#: of the internal, per-run `CSVExportResult.filename` /
#: `PDFExportResult.filename` (which remain unique per `export_id` for
#: potential future consumers such as email delivery or archival).
CSV_DOWNLOAD_FILENAME = "prediction_history.csv"
PDF_DOWNLOAD_FILENAME = "prediction_report.pdf"

#: Chunk size used to stream an already-generated export document back to
#: the client (Phase 6.6, ADR-042). Purely a transfer-layer concern -- it
#: never changes the bytes the client receives, only how many `Response`
#: writes deliver them.
EXPORT_STREAM_CHUNK_SIZE = 64 * 1024

#: Shared `413` documentation fragment for the export-limit responses
#: Phase 6.6 adds to every endpoint below.
EXPORT_LIMIT_EXCEEDED_RESPONSE = {
    "description": (
        "The authenticated user's matching prediction history, or the "
        "generated export document, exceeds a configured Reporting limit."
    ),
    "content": {"application/json": {"example": EXPORT_LIMIT_EXCEEDED_EXAMPLE}},
}


def _iter_export_chunks(content: bytes) -> Iterator[bytes]:
    """Yield `content` in fixed-size chunks for `StreamingResponse` (Phase 6.6, ADR-042).

    A pure, side-effect-free transfer-layer helper: `content` has already
    been fully generated by `CSVExportBuilder`/`PDFBuilder` before this
    runs, so chunking here changes nothing about the document itself --
    only how it is written to the response stream.
    """
    for start in range(0, len(content), EXPORT_STREAM_CHUNK_SIZE):
        yield content[start : start + EXPORT_STREAM_CHUNK_SIZE]


@router.get(
    "/analytics",
    status_code=status.HTTP_200_OK,
    summary="Retrieve aggregated prediction analytics for the authenticated user",
    description=(
        "Returns aggregated prediction statistics computed from the "
        "authenticated user's own prediction history (Phase 6.2, "
        "ADR-038) -- total/successful/failed prediction counts, success "
        "rate, average confidence, average agreement ratio, class "
        "distribution, and confidence distribution, among other figures. "
        "This is a read-only operation: no AI inference, model loading, "
        "or prediction recalculation occurs here, and no prediction "
        "history record is ever modified. Ownership is enforced at the "
        "underlying repository query, so a user can never receive "
        "another user's analytics."
    ),
    response_model=APIResponse[PredictionAnalyticsResponseSchema],
    responses={
        200: {"description": "Aggregated prediction analytics were computed successfully."},
        401: {
            "description": "Missing or invalid authentication credentials.",
            "content": {"application/json": {"example": AUTHENTICATION_ERROR_EXAMPLE}},
        },
        413: EXPORT_LIMIT_EXCEEDED_RESPONSE,
        500: {
            "description": "An unexpected internal server error occurred.",
            "content": {"application/json": {"example": INTERNAL_ERROR_EXAMPLE}},
        },
    },
)
async def get_prediction_analytics(
    current_user: Annotated[User, Depends(get_current_active_user)],
    analytics_service: Annotated[
        PredictionAnalyticsService, Depends(get_prediction_analytics_service)
    ],
):
    """Return aggregated prediction analytics for the authenticated user's own prediction history.

    Delegates entirely to `PredictionAnalyticsService.compute_analytics()`,
    scoped to `current_user.id`. No aggregation, filtering, or business
    logic is performed in this router beyond passing the authenticated
    user's own identifier through and projecting the result onto its
    public schema (ADR-038).
    """
    user_id = str(current_user.id)

    logger.info("Prediction analytics requested: user_id=%s", user_id)

    result = await analytics_service.compute_analytics(user_id=user_id)

    logger.info(
        "Prediction analytics completed: user_id=%s analytics_id=%s total_predictions=%d",
        user_id,
        result.analytics_id,
        result.total_predictions,
    )

    response_data = PredictionAnalyticsResponseSchema.from_domain(result)

    return success_response(
        data=response_data.model_dump(mode="json"),
        message="Prediction analytics retrieved successfully.",
    )


@router.get(
    "/export/csv",
    status_code=status.HTTP_200_OK,
    summary="Download the authenticated user's prediction history and analytics as CSV",
    description=(
        "Generates and streams a downloadable `text/csv` document "
        "containing the authenticated user's complete prediction history "
        "followed by an analytics summary section (Phase 6.3, ADR-039). "
        "This is a read-only operation: no AI inference occurs, and no "
        "prediction data is ever modified. Ownership is enforced at the "
        "underlying repository query, so a user can never download "
        "another user's history."
    ),
    responses={
        200: {
            "description": "The CSV document was generated and is being downloaded.",
            "content": {"text/csv": {}},
        },
        401: {
            "description": "Missing or invalid authentication credentials.",
            "content": {"application/json": {"example": AUTHENTICATION_ERROR_EXAMPLE}},
        },
        413: EXPORT_LIMIT_EXCEEDED_RESPONSE,
        500: {
            "description": "An unexpected internal server error occurred.",
            "content": {"application/json": {"example": INTERNAL_ERROR_EXAMPLE}},
        },
    },
)
async def export_prediction_history_csv(
    current_user: Annotated[User, Depends(get_current_active_user)],
    csv_export_service: Annotated[CSVExportService, Depends(get_csv_export_service)],
):
    """Stream the authenticated user's prediction history and analytics as a CSV download.

    Delegates entirely to `CSVExportService.export_csv()`, scoped to
    `current_user.id`. No serialization, aggregation, or business logic
    is performed in this router beyond passing the authenticated user's
    own identifier through and streaming the already-serialized
    `CSVExportResult.content` back as a downloadable HTTP response
    (ADR-039), in fixed-size chunks rather than a single in-memory body
    (Phase 6.6, ADR-042).
    """
    user_id = str(current_user.id)

    logger.info("CSV export requested: user_id=%s", user_id)

    result = await csv_export_service.export_csv(user_id=user_id)

    logger.info(
        "CSV export completed: user_id=%s export_id=%s record_count=%d",
        user_id,
        result.export_id,
        result.history_row_count,
    )

    return StreamingResponse(
        _iter_export_chunks(result.content.encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{CSV_DOWNLOAD_FILENAME}"'},
    )


@router.get(
    "/export/pdf",
    status_code=status.HTTP_200_OK,
    summary="Download the authenticated user's prediction history and analytics as a PDF report",
    description=(
        "Generates and streams a downloadable `application/pdf` report "
        "containing the authenticated user's analytics summary and "
        "prediction history table (Phase 6.4, ADR-040). This is a "
        "read-only operation: no AI inference occurs, and no prediction "
        "data is ever modified. Ownership is enforced at the underlying "
        "repository query, so a user can never download another user's "
        "report."
    ),
    responses={
        200: {
            "description": "The PDF report was generated and is being downloaded.",
            "content": {"application/pdf": {}},
        },
        401: {
            "description": "Missing or invalid authentication credentials.",
            "content": {"application/json": {"example": AUTHENTICATION_ERROR_EXAMPLE}},
        },
        413: EXPORT_LIMIT_EXCEEDED_RESPONSE,
        500: {
            "description": "An unexpected internal server error occurred.",
            "content": {"application/json": {"example": INTERNAL_ERROR_EXAMPLE}},
        },
    },
)
async def export_prediction_report_pdf(
    current_user: Annotated[User, Depends(get_current_active_user)],
    pdf_export_service: Annotated[PDFExportService, Depends(get_pdf_export_service)],
):
    """Stream the authenticated user's prediction history and analytics as a PDF download.

    Delegates entirely to `PDFExportService.export_pdf()`, scoped to
    `current_user.id`. No rendering, aggregation, or business logic is
    performed in this router beyond passing the authenticated user's own
    identifier through and streaming the already-rendered
    `PDFExportResult.content` back as a downloadable HTTP response
    (ADR-040), in fixed-size chunks rather than a single in-memory body
    (Phase 6.6, ADR-042).
    """
    user_id = str(current_user.id)

    logger.info("PDF export requested: user_id=%s", user_id)

    result = await pdf_export_service.export_pdf(user_id=user_id)

    logger.info(
        "PDF export completed: user_id=%s export_id=%s record_count=%d",
        user_id,
        result.export_id,
        result.history_row_count,
    )

    return StreamingResponse(
        _iter_export_chunks(result.content),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{PDF_DOWNLOAD_FILENAME}"'},
    )
