"""Tests for `PDFBuilder` (Phase 6.4, ADR-040)."""

from app.history.enums import PredictionHistoryStatus
from app.reports.analytics.analytics_result import PredictionAnalyticsResult
from app.reports.pdf.pdf_builder import (
    HISTORY_COLUMNS,
    PDFBuilder,
    _format_percentage,
    _format_ratio,
)
from tests.reports.conftest_helpers import make_history_record, make_summary


def _empty_analytics() -> PredictionAnalyticsResult:
    return PredictionAnalyticsResult.empty(
        analytics_id="analytics-0001", user_id="user-0001", generated_at="2026-08-01T00:00:00+00:00"
    )


class TestFormattingHelpers:
    """Verifies the shared, deterministic numeric formatting helpers."""

    def test_format_percentage_always_uses_two_decimal_places(self) -> None:
        assert _format_percentage(90.0) == "90.00%"
        assert _format_percentage(90) == "90.00%"
        assert _format_percentage(87.5) == "87.50%"

    def test_format_ratio_always_uses_four_decimal_places(self) -> None:
        assert _format_ratio(1.0) == "1.0000"
        assert _format_ratio(0.925) == "0.9250"


class TestPDFExportBuilderEmptyHistory:
    """Verifies `PDFBuilder.build()` for an empty history collection."""

    def test_empty_history_returns_zero_row_count(self) -> None:
        result = PDFBuilder().build(user_id="user-0001", history=[], analytics=_empty_analytics())

        assert result.history_row_count == 0
        assert result.user_id == "user-0001"

    def test_empty_history_still_produces_a_valid_pdf_document(self) -> None:
        result = PDFBuilder().build(user_id="user-0001", history=[], analytics=_empty_analytics())

        assert result.content.startswith(b"%PDF")
        assert len(result.content) > 0

    def test_content_type_is_application_pdf(self) -> None:
        result = PDFBuilder().build(user_id="user-0001", history=[], analytics=_empty_analytics())

        assert result.content_type == "application/pdf"

    def test_filename_is_unique_per_export_and_ends_with_pdf(self) -> None:
        builder = PDFBuilder()

        first = builder.build(user_id="user-0001", history=[], analytics=_empty_analytics())
        second = builder.build(user_id="user-0001", history=[], analytics=_empty_analytics())

        assert first.filename != second.filename
        assert first.filename.endswith(".pdf")

    def test_each_build_call_produces_a_unique_export_id(self) -> None:
        builder = PDFBuilder()

        first = builder.build(user_id="user-0001", history=[], analytics=_empty_analytics())
        second = builder.build(user_id="user-0001", history=[], analytics=_empty_analytics())

        assert first.export_id != second.export_id


class TestPDFExportBuilderPopulatedHistory:
    """Verifies `PDFBuilder.build()` rendering over a populated history collection."""

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
        result = PDFBuilder().build(
            user_id="user-0001", history=self._build_sample_history(), analytics=_empty_analytics()
        )

        assert result.history_row_count == 2

    def test_renders_a_non_trivial_pdf_document(self) -> None:
        result = PDFBuilder().build(
            user_id="user-0001", history=self._build_sample_history(), analytics=_empty_analytics()
        )

        assert result.content.startswith(b"%PDF")
        assert len(result.content) > 500

    def test_history_table_follows_the_deterministic_column_order(self) -> None:
        table = PDFBuilder._build_history_table(self._build_sample_history())

        assert table._cellvalues[0] == list(HISTORY_COLUMNS)

    def test_history_table_rows_reflect_the_supplied_records(self) -> None:
        table = PDFBuilder._build_history_table(self._build_sample_history())

        assert table._cellvalues[1] == [
            "req-0001",
            "2026-07-27T10:00:00+00:00",
            "lung_aca",
            "90.00%",
            "1.0000",
            "success",
        ]

    def test_failed_record_has_placeholder_predicted_class(self) -> None:
        table = PDFBuilder._build_history_table(self._build_sample_history())

        failed_row = table._cellvalues[2]
        assert failed_row[0] == "req-0002"
        assert failed_row[2] == "N/A"
        assert failed_row[5] == "failed"

    def test_analytics_table_reflects_the_supplied_analytics_result_verbatim(self) -> None:
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

        table = PDFBuilder._build_analytics_table(analytics)
        rows = {row[0]: row[1] for row in table._cellvalues[1:]}

        assert rows["Total Predictions"] == "2"
        assert rows["Successful Predictions"] == "1"
        assert rows["Failed Predictions"] == "1"
        assert rows["Average Confidence"] == "90.00%"
        assert rows["Average Agreement Ratio"] == "1.0000"
        assert rows["Most Predicted Class"] == "lung_aca"

    def test_never_mutates_the_supplied_history_records(self) -> None:
        history = self._build_sample_history()
        original_snapshot = [record.model_copy(deep=True) for record in history]

        PDFBuilder().build(user_id="user-0001", history=history, analytics=_empty_analytics())

        assert history == original_snapshot

    def test_special_characters_in_dynamic_fields_do_not_break_rendering(self) -> None:
        history = [
            make_history_record(
                history_id="hist-0003",
                request_id="req-<injected>&\"quoted\"",
                summary=make_summary(predicted_class="colon_n & café"),
            )
        ]

        result = PDFBuilder().build(user_id="user-0001", history=history, analytics=_empty_analytics())

        assert result.content.startswith(b"%PDF")
