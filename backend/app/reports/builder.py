"""Report Builder (Phase 6.1, ADR-037).

`ReportBuilder` is the pure aggregation layer that assembles an immutable
`Report` from an already-retrieved `PredictionHistory` collection. It
never accesses the database, never verifies ownership, never performs
inference, and never generates a report file of any format -- it only
copies and aggregates values already present on the supplied
`PredictionHistory` records, mirroring the read-only, copy-only
convention already established by `PredictionHistoryMapper`.
"""

from app.core.logging import get_logger
from app.history.enums import PredictionHistoryStatus
from app.history.prediction_history import PredictionHistory
from app.reports.enums import ReportStatus
from app.reports.report import Report
from app.reports.statistics import ReportStatistics
from app.reports.summary import ReportSummary
from app.utils.environment import generate_request_id, get_current_timestamp

logger = get_logger(__name__)


class ReportBuilder:
    """Builds immutable `Report` objects from a prediction history collection.

    Stateless and side-effect free beyond logging. Holds no per-request
    state between calls, so a single instance may be reused, or
    constructed, per request -- mirroring the same convention already
    used by `PredictionHistoryMapper` and `PredictionResponseBuilder`.
    """

    def build(self, user_id: str, history: list[PredictionHistory]) -> Report:
        """Build a `Report` from an already-retrieved `PredictionHistory` collection.

        Args:
            user_id: Identifier of the user this report is generated for.
                Copied directly onto the resulting `Report` -- this method
                performs no ownership verification of its own; `history`
                is trusted to already be scoped to `user_id` by the
                repository query that produced it.
            history: The user's `PredictionHistory` records to aggregate,
                typically newest first. May be empty.

        Returns:
            An immutable `Report`. `Report.empty()` when `history` is
            empty; otherwise a `GENERATED` report carrying a
            `ReportSummary`, a `ReportStatistics`, and `history` itself.
        """
        report_id = generate_request_id()
        generated_at = get_current_timestamp()

        if not history:
            logger.info(
                "Report built with empty history collection: user_id=%s report_id=%s",
                user_id,
                report_id,
            )
            return Report.empty(report_id=report_id, user_id=user_id, generated_at=generated_at)

        report = Report(
            report_id=report_id,
            user_id=user_id,
            generated_at=generated_at,
            status=ReportStatus.GENERATED,
            summary=self._build_summary(history),
            statistics=self._build_statistics(history),
            history=history,
        )

        logger.info(
            "Report built: user_id=%s report_id=%s record_count=%d",
            user_id,
            report_id,
            len(history),
        )

        return report

    @staticmethod
    def _build_summary(history: list[PredictionHistory]) -> ReportSummary:
        """Aggregate the high-level `ReportSummary` for `history`.

        Determines the oldest/newest record by `created_at` directly,
        rather than assuming any particular ordering of `history` itself.
        """
        timestamps = [record.created_at for record in history]

        return ReportSummary(
            total_predictions=len(history),
            first_prediction_at=min(timestamps),
            latest_prediction_at=max(timestamps),
        )

    @staticmethod
    def _build_statistics(history: list[PredictionHistory]) -> ReportStatistics:
        """Aggregate the `ReportStatistics` for `history`.

        Every value is derived from fields the prediction pipeline and
        `PredictionHistoryMapper` already computed -- no confidence,
        agreement, or vote recalculation of any kind occurs here.
        """
        successful = 0
        partial_success = 0
        failed = 0
        confidences: list[float] = []
        agreement_ratios: list[float] = []
        distribution: dict[str, int] = {}

        for record in history:
            if record.status == PredictionHistoryStatus.SUCCESS:
                successful += 1
            elif record.status == PredictionHistoryStatus.PARTIAL_SUCCESS:
                partial_success += 1
            elif record.status == PredictionHistoryStatus.FAILED:
                failed += 1

            predicted_class = record.summary.predicted_class
            if predicted_class is None:
                continue

            confidences.append(record.summary.confidence)
            agreement_ratios.append(record.summary.agreement_ratio)
            distribution[predicted_class] = distribution.get(predicted_class, 0) + 1

        most_predicted_class = (
            max(distribution, key=distribution.get) if distribution else None
        )

        return ReportStatistics(
            successful_predictions=successful,
            partial_success_predictions=partial_success,
            failed_predictions=failed,
            average_confidence=(
                round(sum(confidences) / len(confidences), 2) if confidences else 0.0
            ),
            average_agreement_ratio=(
                round(sum(agreement_ratios) / len(agreement_ratios), 4)
                if agreement_ratios
                else 0.0
            ),
            most_predicted_class=most_predicted_class,
            prediction_distribution=distribution,
        )
