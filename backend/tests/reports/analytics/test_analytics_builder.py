"""Tests for `AnalyticsBuilder` (Phase 6.2, ADR-038)."""

from datetime import datetime, timezone

from app.reports.analytics.analytics_builder import AnalyticsBuilder
from tests.reports.conftest_helpers import make_history_record, make_summary


class TestAnalyticsBuilderEmptyHistory:
    """Verifies `AnalyticsBuilder.build()` for an empty history collection."""

    def test_empty_history_returns_empty_result(self) -> None:
        builder = AnalyticsBuilder()

        result = builder.build(user_id="user-0001", history=[])

        assert result.user_id == "user-0001"
        assert result.total_predictions == 0
        assert result.successful_predictions == 0
        assert result.failed_predictions == 0
        assert result.success_rate == 0.0
        assert result.average_confidence == 0.0
        assert result.average_agreement_ratio == 0.0
        assert result.most_predicted_class is None
        assert result.class_distribution == {}
        assert result.first_prediction_date is None
        assert result.latest_prediction_date is None
        assert result.predictions_today == 0
        assert result.predictions_this_week == 0
        assert result.predictions_this_month == 0


class TestAnalyticsBuilderPopulatedHistory:
    """Verifies `AnalyticsBuilder.build()` aggregation over a populated history collection."""

    def _build_sample_history(self) -> list:
        return [
            make_history_record(
                history_id="hist-0001",
                created_at="2026-07-27T10:00:00+00:00",
                summary=make_summary(predicted_class="lung_aca", confidence=90.0, agreement_ratio=1.0),
            ),
            make_history_record(
                history_id="hist-0002",
                created_at="2026-07-28T10:00:00+00:00",
                summary=make_summary(predicted_class="lung_scc", confidence=70.0, agreement_ratio=0.5),
            ),
            make_history_record(
                history_id="hist-0003",
                created_at="2026-07-26T10:00:00+00:00",
                summary=make_summary(predicted_class=None, confidence=0.0, agreement_ratio=0.0),
            ),
            make_history_record(
                history_id="hist-0004",
                created_at="2026-07-29T10:00:00+00:00",
                summary=make_summary(predicted_class="lung_aca", confidence=80.0, agreement_ratio=1.0),
            ),
        ]

    def test_total_predictions(self) -> None:
        result = AnalyticsBuilder().build(user_id="user-0001", history=self._build_sample_history())

        assert result.total_predictions == 4

    def test_successful_and_failed_predictions(self) -> None:
        result = AnalyticsBuilder().build(user_id="user-0001", history=self._build_sample_history())

        assert result.successful_predictions == 3
        assert result.failed_predictions == 1

    def test_success_rate(self) -> None:
        result = AnalyticsBuilder().build(user_id="user-0001", history=self._build_sample_history())

        assert result.success_rate == 75.0

    def test_average_confidence_excludes_records_without_a_predicted_class(self) -> None:
        result = AnalyticsBuilder().build(user_id="user-0001", history=self._build_sample_history())

        # (90.0 + 70.0 + 80.0) / 3 == 80.0
        assert result.average_confidence == 80.0

    def test_average_agreement_ratio_excludes_records_without_a_predicted_class(self) -> None:
        result = AnalyticsBuilder().build(user_id="user-0001", history=self._build_sample_history())

        assert round(result.average_agreement_ratio, 4) == round((1.0 + 0.5 + 1.0) / 3, 4)

    def test_class_distribution_counts_per_class(self) -> None:
        result = AnalyticsBuilder().build(user_id="user-0001", history=self._build_sample_history())

        assert result.class_distribution == {"lung_aca": 2, "lung_scc": 1}

    def test_most_predicted_class(self) -> None:
        result = AnalyticsBuilder().build(user_id="user-0001", history=self._build_sample_history())

        assert result.most_predicted_class == "lung_aca"

    def test_first_and_latest_prediction_date_regardless_of_input_order(self) -> None:
        result = AnalyticsBuilder().build(user_id="user-0001", history=self._build_sample_history())

        assert result.first_prediction_date == "2026-07-26T10:00:00+00:00"
        assert result.latest_prediction_date == "2026-07-29T10:00:00+00:00"

    def test_each_build_call_produces_a_unique_analytics_id(self) -> None:
        builder = AnalyticsBuilder()
        history = self._build_sample_history()

        first = builder.build(user_id="user-0001", history=history)
        second = builder.build(user_id="user-0001", history=history)

        assert first.analytics_id != second.analytics_id

    def test_never_mutates_the_supplied_history_records(self) -> None:
        history = self._build_sample_history()
        original_snapshot = [record.model_copy(deep=True) for record in history]

        AnalyticsBuilder().build(user_id="user-0001", history=history)

        assert history == original_snapshot


class TestAnalyticsBuilderPeriodCounts:
    """Verifies `predictions_today` / `predictions_this_week` / `predictions_this_month`."""

    def test_period_counts_relative_to_reference_time(self) -> None:
        # Wednesday, 2026-07-29 12:00 UTC.
        reference = datetime(2026, 7, 29, 12, 0, 0, tzinfo=timezone.utc)

        history = [
            make_history_record(
                history_id="hist-today",
                created_at="2026-07-29T01:00:00+00:00",
            ),
            make_history_record(
                history_id="hist-this-week",
                created_at="2026-07-27T09:00:00+00:00",
            ),
            make_history_record(
                history_id="hist-this-month-only",
                created_at="2026-07-05T09:00:00+00:00",
            ),
            make_history_record(
                history_id="hist-last-month",
                created_at="2026-06-15T09:00:00+00:00",
            ),
        ]

        result = AnalyticsBuilder().build(user_id="user-0001", history=history, reference_time=reference)

        assert result.predictions_today == 1
        assert result.predictions_this_week == 2
        assert result.predictions_this_month == 3

    def test_defaults_to_current_time_when_reference_time_omitted(self) -> None:
        history = [make_history_record(history_id="hist-0001", created_at="2026-07-27T10:00:00+00:00")]

        result = AnalyticsBuilder().build(user_id="user-0001", history=history)

        # No assertion on exact bucket membership (depends on wall-clock
        # time when the test runs) -- only that aggregation completes
        # without a `reference_time` and produces non-negative counts.
        assert result.predictions_today >= 0
        assert result.predictions_this_week >= 0
        assert result.predictions_this_month >= 0
