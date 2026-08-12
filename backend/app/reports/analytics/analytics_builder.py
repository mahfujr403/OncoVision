"""Analytics Builder (Phase 6.2, ADR-038).

`AnalyticsBuilder` is the pure aggregation layer that assembles an
immutable `PredictionAnalyticsResult` from an already-retrieved
`PredictionHistory` collection. It never accesses the database, never
verifies ownership, never performs inference, and never generates a
report file of any format -- it only aggregates values already present
on the supplied `PredictionHistory` records, mirroring the read-only,
copy-only convention already established by `ReportBuilder`.
"""

from datetime import datetime, timedelta, timezone

from app.core.logging import get_logger
from app.history.prediction_history import PredictionHistory
from app.reports.analytics.analytics_result import PredictionAnalyticsResult
from app.utils.environment import generate_request_id, get_current_timestamp

logger = get_logger(__name__)

# Fixed final-confidence percentage bucket boundaries feeding
# `confidence_distribution` (Phase 6.5, ADR-041). Non-configurable, mirroring
# the "internal, non-configurable bound" convention already used elsewhere in
# `app.reports` (e.g. `ReportService.REPORT_HISTORY_LIMIT`). Each tuple is
# `(label, lower_bound_inclusive, upper_bound_exclusive)`; the final bucket's
# upper bound is treated as inclusive so a 100.0 confidence value is counted.
CONFIDENCE_DISTRIBUTION_BUCKETS: tuple[tuple[str, float, float], ...] = (
    ("0-20", 0.0, 20.0),
    ("20-40", 20.0, 40.0),
    ("40-60", 40.0, 60.0),
    ("60-80", 60.0, 80.0),
    ("80-100", 80.0, 100.0),
)


class AnalyticsBuilder:
    """Builds immutable `PredictionAnalyticsResult` objects from a prediction history collection.

    Stateless and side-effect free beyond logging. Holds no per-request
    state between calls, so a single instance may be reused, or
    constructed, per request -- mirroring the same convention already
    used by `ReportBuilder`.
    """

    def build(
        self,
        user_id: str,
        history: list[PredictionHistory],
        reference_time: datetime | None = None,
    ) -> PredictionAnalyticsResult:
        """Build a `PredictionAnalyticsResult` from an already-retrieved `PredictionHistory` collection.

        Args:
            user_id: Identifier of the user this analytics computation is
                for. Copied directly onto the resulting result -- this
                method performs no ownership verification of its own;
                `history` is trusted to already be scoped to `user_id` by
                the repository query that produced it.
            history: The user's `PredictionHistory` records to aggregate.
                May be supplied in any order. May be empty.
            reference_time: The timestamp `predictions_today` /
                `predictions_this_week` / `predictions_this_month` are
                computed relative to. Defaults to the current UTC time.
                Exposed as a parameter so callers (and tests) can compute
                deterministic, reproducible results.

        Returns:
            An immutable `PredictionAnalyticsResult`.
            `PredictionAnalyticsResult.empty()` when `history` is empty;
            otherwise a fully aggregated result.
        """
        analytics_id = generate_request_id()
        generated_at = get_current_timestamp()

        if not history:
            logger.info(
                "Analytics built with empty history collection: user_id=%s analytics_id=%s",
                user_id,
                analytics_id,
            )
            return PredictionAnalyticsResult.empty(
                analytics_id=analytics_id, user_id=user_id, generated_at=generated_at
            )

        reference = reference_time or datetime.now(timezone.utc)

        result = PredictionAnalyticsResult(
            analytics_id=analytics_id,
            user_id=user_id,
            generated_at=generated_at,
            **self._aggregate(history, reference),
        )

        logger.info(
            "Analytics built: user_id=%s analytics_id=%s record_count=%d",
            user_id,
            analytics_id,
            len(history),
        )

        return result

    @classmethod
    def _aggregate(cls, history: list[PredictionHistory], reference: datetime) -> dict:
        """Aggregate every `PredictionAnalyticsResult` field except its identity fields.

        Every value is derived from fields the prediction pipeline and
        `PredictionHistoryMapper` already computed -- no confidence,
        agreement, or vote recalculation of any kind occurs here.
        """
        total = len(history)
        successful = 0
        confidences: list[float] = []
        agreement_ratios: list[float] = []
        distribution: dict[str, int] = {}
        confidence_distribution: dict[str, int] = {}
        timestamps = [record.created_at for record in history]

        today_start, week_start, month_start = cls._period_boundaries(reference)
        predictions_today = 0
        predictions_this_week = 0
        predictions_this_month = 0

        for record in history:
            predicted_class = record.summary.predicted_class
            if predicted_class is not None:
                successful += 1
                confidences.append(record.summary.confidence)
                agreement_ratios.append(record.summary.agreement_ratio)
                distribution[predicted_class] = distribution.get(predicted_class, 0) + 1
                bucket_label = cls._bucket_confidence(record.summary.confidence)
                if bucket_label is not None:
                    confidence_distribution[bucket_label] = (
                        confidence_distribution.get(bucket_label, 0) + 1
                    )

            created_at = cls._parse_timestamp(record.created_at)
            if created_at is None:
                continue

            if created_at >= today_start:
                predictions_today += 1
            if created_at >= week_start:
                predictions_this_week += 1
            if created_at >= month_start:
                predictions_this_month += 1

        failed = total - successful
        most_predicted_class = max(distribution, key=distribution.get) if distribution else None

        return {
            "total_predictions": total,
            "successful_predictions": successful,
            "failed_predictions": failed,
            "success_rate": round((successful / total) * 100, 2) if total else 0.0,
            "average_confidence": (
                round(sum(confidences) / len(confidences), 2) if confidences else 0.0
            ),
            "average_agreement_ratio": (
                round(sum(agreement_ratios) / len(agreement_ratios), 4)
                if agreement_ratios
                else 0.0
            ),
            "most_predicted_class": most_predicted_class,
            "class_distribution": distribution,
            "confidence_distribution": confidence_distribution,
            "first_prediction_date": min(timestamps),
            "latest_prediction_date": max(timestamps),
            "predictions_today": predictions_today,
            "predictions_this_week": predictions_this_week,
            "predictions_this_month": predictions_this_month,
        }

    @staticmethod
    def _bucket_confidence(confidence: float) -> str | None:
        """Return the `CONFIDENCE_DISTRIBUTION_BUCKETS` label `confidence` falls into.

        `confidence` is expected on the standard 0-100 percentage scale
        already used by `PredictionHistorySummary.confidence`. Returns
        `None` for an out-of-range value (defensive only -- this should
        never occur for a real prediction result) rather than raising, so
        a single malformed value never fails an entire analytics
        computation, mirroring `_parse_timestamp()`'s defensive convention.
        """
        for label, lower, upper in CONFIDENCE_DISTRIBUTION_BUCKETS:
            if lower <= confidence < upper:
                return label
        if confidence == CONFIDENCE_DISTRIBUTION_BUCKETS[-1][2]:
            return CONFIDENCE_DISTRIBUTION_BUCKETS[-1][0]
        return None

    @staticmethod
    def _period_boundaries(reference: datetime) -> tuple[datetime, datetime, datetime]:
        """Return the (today, this-week, this-month) start boundaries for `reference`.

        `today_start` is midnight UTC on `reference`'s calendar day.
        `week_start` is midnight UTC on the Monday of `reference`'s ISO
        week. `month_start` is midnight UTC on the first day of
        `reference`'s calendar month.
        """
        today_start = reference.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)
        return today_start, week_start, month_start

    @staticmethod
    def _parse_timestamp(value: str) -> datetime | None:
        """Parse an ISO 8601 `PredictionHistory.created_at` string into a `datetime`.

        Returns `None` (logged) for a malformed value rather than raising,
        so a single unparsable record never fails an entire analytics
        computation.
        """
        try:
            return datetime.fromisoformat(value)
        except (ValueError, TypeError):
            logger.warning("Analytics aggregation skipped an unparsable created_at value.")
            return None
