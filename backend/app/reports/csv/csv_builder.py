"""CSV Export Builder (Phase 6.3, ADR-039).

`CSVExportBuilder` is the pure serialization layer that assembles an
immutable `CSVExportResult` from an already-retrieved `PredictionHistory`
collection and an already-computed `PredictionAnalyticsResult`. It never
accesses the database, never verifies ownership, never performs
inference, and never recalculates any statistic -- it only formats
values already present on the supplied domain objects as CSV text,
mirroring the read-only, copy-only convention already established by
`ReportBuilder` and `AnalyticsBuilder`.

The generated document is UTF-8 text with two sections, each carrying
its own deterministic header row:

    Prediction History
        request_id, prediction_date, predicted_class, confidence,
        agreement_ratio, participating_models, status

    Analytics Summary
        metric, value
"""

import csv
import io

from app.core.logging import get_logger
from app.history.prediction_history import PredictionHistory
from app.reports.analytics.analytics_result import PredictionAnalyticsResult
from app.reports.csv.csv_result import CSVExportResult
from app.utils.environment import generate_request_id, get_current_timestamp

logger = get_logger(__name__)

#: Deterministic column order for the Prediction History section.
#: `CSVExportBuilder` never reorders, renames, or omits these columns.
HISTORY_COLUMNS: tuple[str, ...] = (
    "request_id",
    "prediction_date",
    "predicted_class",
    "confidence",
    "agreement_ratio",
    "participating_models",
    "status",
)

#: Deterministic row order for the Analytics Summary section.
ANALYTICS_METRICS: tuple[str, ...] = (
    "total_predictions",
    "successful_predictions",
    "failed_predictions",
    "success_rate",
    "average_confidence",
    "average_agreement_ratio",
    "most_predicted_class",
)


class CSVExportBuilder:
    """Builds immutable `CSVExportResult` objects from prediction history and analytics.

    Stateless and side-effect free beyond logging. Holds no per-request
    state between calls, so a single instance may be reused, or
    constructed, per request -- mirroring the same convention already
    used by `ReportBuilder` and `AnalyticsBuilder`.
    """

    def build(
        self,
        user_id: str,
        history: list[PredictionHistory],
        analytics: PredictionAnalyticsResult,
    ) -> CSVExportResult:
        """Build a `CSVExportResult` from already-retrieved data.

        Args:
            user_id: Identifier of the user this export is generated for.
                Copied directly onto the resulting `CSVExportResult` --
                this method performs no ownership verification of its
                own; `history` and `analytics` are trusted to already be
                scoped to `user_id` by the repository/service calls that
                produced them.
            history: The user's `PredictionHistory` records to serialize
                into the Prediction History section. May be supplied in
                any order. May be empty.
            analytics: The user's already-computed
                `PredictionAnalyticsResult`, serialized into the
                Analytics Summary section verbatim -- no recalculation
                occurs here.

        Returns:
            An immutable `CSVExportResult` carrying the complete CSV
            document as UTF-8 text.
        """
        export_id = generate_request_id()
        generated_at = get_current_timestamp()
        filename = self._build_filename(export_id)

        content = self._serialize(history=history, analytics=analytics)

        if not history:
            logger.info(
                "CSV export built with empty history collection: user_id=%s export_id=%s",
                user_id,
                export_id,
            )
            return CSVExportResult.empty(
                export_id=export_id,
                user_id=user_id,
                generated_at=generated_at,
                filename=filename,
                content=content,
            )

        result = CSVExportResult(
            export_id=export_id,
            user_id=user_id,
            generated_at=generated_at,
            filename=filename,
            content=content,
            history_row_count=len(history),
        )

        logger.info(
            "CSV export built: user_id=%s export_id=%s record_count=%d",
            user_id,
            export_id,
            len(history),
        )

        return result

    @classmethod
    def _serialize(
        cls,
        history: list[PredictionHistory],
        analytics: PredictionAnalyticsResult,
    ) -> str:
        """Serialize `history` and `analytics` into the complete CSV document text.

        Uses `csv.writer` (not manual string concatenation) so comma- or
        quote-containing field values -- for example a model name -- are
        always escaped per the CSV format, rather than corrupting column
        alignment.
        """
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")

        writer.writerow(HISTORY_COLUMNS)
        for record in history:
            writer.writerow(cls._history_row(record))

        writer.writerow([])
        writer.writerow(["Analytics Summary"])
        writer.writerow(["metric", "value"])
        for row in cls._analytics_rows(analytics):
            writer.writerow(row)

        return buffer.getvalue()

    @staticmethod
    def _history_row(record: PredictionHistory) -> tuple:
        """Project one `PredictionHistory` record onto a `HISTORY_COLUMNS`-ordered row."""
        return (
            record.request_id,
            record.created_at,
            record.summary.predicted_class or "",
            record.summary.confidence,
            record.summary.agreement_ratio,
            "; ".join(record.summary.successful_models),
            record.status.value,
        )

    @staticmethod
    def _analytics_rows(analytics: PredictionAnalyticsResult) -> list[tuple]:
        """Project `analytics` onto `ANALYTICS_METRICS`-ordered (metric, value) rows."""
        values = {
            "total_predictions": analytics.total_predictions,
            "successful_predictions": analytics.successful_predictions,
            "failed_predictions": analytics.failed_predictions,
            "success_rate": analytics.success_rate,
            "average_confidence": analytics.average_confidence,
            "average_agreement_ratio": analytics.average_agreement_ratio,
            "most_predicted_class": analytics.most_predicted_class or "",
        }
        return [(metric, values[metric]) for metric in ANALYTICS_METRICS]

    @staticmethod
    def _build_filename(export_id: str) -> str:
        """Return the suggested filename for one export run, unique per `export_id`."""
        return f"oncovision_prediction_export_{export_id}.csv"
