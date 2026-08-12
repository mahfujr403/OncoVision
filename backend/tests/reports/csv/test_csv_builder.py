"""Tests for `CSVExportBuilder` (Phase 6.3, ADR-039)."""

import csv
import io

from app.history.enums import PredictionHistoryStatus
from app.reports.analytics.analytics_result import PredictionAnalyticsResult
from app.reports.csv.csv_builder import CSVExportBuilder, HISTORY_COLUMNS
from tests.reports.conftest_helpers import make_history_record, make_summary


def _parse_sections(content: str) -> list[list[str]]:
    """Parse `content` back into rows using `csv.reader`, verifying it round-trips."""
    return list(csv.reader(io.StringIO(content)))


class TestCSVExportBuilderEmptyHistory:
    """Verifies `CSVExportBuilder.build()` for an empty history collection."""

    def test_empty_history_returns_zero_row_count(self) -> None:
        analytics = PredictionAnalyticsResult.empty(
            analytics_id="analytics-0001", user_id="user-0001", generated_at="2026-08-01T00:00:00+00:00"
        )

        result = CSVExportBuilder().build(user_id="user-0001", history=[], analytics=analytics)

        assert result.history_row_count == 0
        assert result.user_id == "user-0001"

    def test_empty_history_still_produces_a_valid_header_row(self) -> None:
        analytics = PredictionAnalyticsResult.empty(
            analytics_id="analytics-0001", user_id="user-0001", generated_at="2026-08-01T00:00:00+00:00"
        )

        result = CSVExportBuilder().build(user_id="user-0001", history=[], analytics=analytics)
        rows = _parse_sections(result.content)

        assert rows[0] == list(HISTORY_COLUMNS)

    def test_empty_history_analytics_section_has_zero_data_values(self) -> None:
        analytics = PredictionAnalyticsResult.empty(
            analytics_id="analytics-0001", user_id="user-0001", generated_at="2026-08-01T00:00:00+00:00"
        )

        result = CSVExportBuilder().build(user_id="user-0001", history=[], analytics=analytics)
        rows = _parse_sections(result.content)

        metrics = {row[0]: row[1] for row in rows if len(row) == 2 and row[0] != "metric"}
        assert metrics["total_predictions"] == "0"
        assert metrics["most_predicted_class"] == ""

    def test_filename_is_unique_per_export_and_ends_with_csv(self) -> None:
        analytics = PredictionAnalyticsResult.empty(
            analytics_id="analytics-0001", user_id="user-0001", generated_at="2026-08-01T00:00:00+00:00"
        )
        builder = CSVExportBuilder()

        first = builder.build(user_id="user-0001", history=[], analytics=analytics)
        second = builder.build(user_id="user-0001", history=[], analytics=analytics)

        assert first.filename != second.filename
        assert first.filename.endswith(".csv")


class TestCSVExportBuilderPopulatedHistory:
    """Verifies `CSVExportBuilder.build()` serialization over a populated history collection."""

    def _build_sample_history(self) -> list:
        return [
            make_history_record(
                history_id="hist-0001",
                request_id="req-0001",
                created_at="2026-07-27T10:00:00+00:00",
                status=PredictionHistoryStatus.SUCCESS,
                summary=make_summary(
                    predicted_class="lung_aca",
                    confidence=90.0,
                    agreement_ratio=1.0,
                    successful_models=["mobilenetv2", "densenet121"],
                ),
            ),
            make_history_record(
                history_id="hist-0002",
                request_id="req-0002",
                created_at="2026-07-28T10:00:00+00:00",
                status=PredictionHistoryStatus.FAILED,
                summary=make_summary(
                    predicted_class=None,
                    confidence=0.0,
                    agreement_ratio=0.0,
                    successful_models=[],
                ),
            ),
        ]

    def test_history_row_count_matches_supplied_records(self) -> None:
        analytics = PredictionAnalyticsResult.empty(
            analytics_id="analytics-0001", user_id="user-0001", generated_at="2026-08-01T00:00:00+00:00"
        )

        result = CSVExportBuilder().build(
            user_id="user-0001", history=self._build_sample_history(), analytics=analytics
        )

        assert result.history_row_count == 2

    def test_history_rows_follow_the_deterministic_column_order(self) -> None:
        analytics = PredictionAnalyticsResult.empty(
            analytics_id="analytics-0001", user_id="user-0001", generated_at="2026-08-01T00:00:00+00:00"
        )

        result = CSVExportBuilder().build(
            user_id="user-0001", history=self._build_sample_history(), analytics=analytics
        )
        rows = _parse_sections(result.content)

        assert rows[0] == list(HISTORY_COLUMNS)
        assert rows[1] == [
            "req-0001",
            "2026-07-27T10:00:00+00:00",
            "lung_aca",
            "90.0",
            "1.0",
            "mobilenetv2; densenet121",
            "success",
        ]

    def test_failed_record_has_empty_predicted_class_field(self) -> None:
        analytics = PredictionAnalyticsResult.empty(
            analytics_id="analytics-0001", user_id="user-0001", generated_at="2026-08-01T00:00:00+00:00"
        )

        result = CSVExportBuilder().build(
            user_id="user-0001", history=self._build_sample_history(), analytics=analytics
        )
        rows = _parse_sections(result.content)

        failed_row = rows[2]
        assert failed_row[0] == "req-0002"
        assert failed_row[2] == ""
        assert failed_row[6] == "failed"

    def test_analytics_section_reflects_the_supplied_analytics_result_verbatim(self) -> None:
        analytics = PredictionAnalyticsResult(
            analytics_id="analytics-0001",
            user_id="user-0001",
            generated_at="2026-08-01T00:00:00+00:00",
            total_predictions=2,
            successful_predictions=1,
            failed_predictions=1,
            success_rate=50.0,
            average_confidence=90.0,
            average_agreement_ratio=1.0,
            most_predicted_class="lung_aca",
            class_distribution={"lung_aca": 1},
            first_prediction_date="2026-07-27T10:00:00+00:00",
            latest_prediction_date="2026-07-28T10:00:00+00:00",
        )

        result = CSVExportBuilder().build(
            user_id="user-0001", history=self._build_sample_history(), analytics=analytics
        )
        rows = _parse_sections(result.content)

        metrics = {row[0]: row[1] for row in rows if len(row) == 2 and row[0] != "metric"}
        assert metrics["total_predictions"] == "2"
        assert metrics["successful_predictions"] == "1"
        assert metrics["failed_predictions"] == "1"
        assert metrics["success_rate"] == "50.0"
        assert metrics["average_confidence"] == "90.0"
        assert metrics["most_predicted_class"] == "lung_aca"

    def test_never_mutates_the_supplied_history_records(self) -> None:
        history = self._build_sample_history()
        original_snapshot = [record.model_copy(deep=True) for record in history]
        analytics = PredictionAnalyticsResult.empty(
            analytics_id="analytics-0001", user_id="user-0001", generated_at="2026-08-01T00:00:00+00:00"
        )

        CSVExportBuilder().build(user_id="user-0001", history=history, analytics=analytics)

        assert history == original_snapshot

    def test_each_build_call_produces_a_unique_export_id(self) -> None:
        history = self._build_sample_history()
        analytics = PredictionAnalyticsResult.empty(
            analytics_id="analytics-0001", user_id="user-0001", generated_at="2026-08-01T00:00:00+00:00"
        )
        builder = CSVExportBuilder()

        first = builder.build(user_id="user-0001", history=history, analytics=analytics)
        second = builder.build(user_id="user-0001", history=history, analytics=analytics)

        assert first.export_id != second.export_id
