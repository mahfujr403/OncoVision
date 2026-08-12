"""Tests for `ReportBuilder` (Phase 6.1, ADR-037)."""

from app.history.enums import PredictionHistoryStatus
from app.reports.builder import ReportBuilder
from app.reports.enums import ReportStatus
from tests.reports.conftest_helpers import make_history_record, make_summary


class TestReportBuilderEmptyHistory:
    """Verifies `ReportBuilder.build()` for an empty history collection."""

    def test_empty_history_returns_empty_report(self) -> None:
        builder = ReportBuilder()

        report = builder.build(user_id="user-0001", history=[])

        assert report.status == ReportStatus.EMPTY
        assert report.user_id == "user-0001"
        assert report.history == []

    def test_empty_report_has_zero_data_summary(self) -> None:
        report = ReportBuilder().build(user_id="user-0001", history=[])

        assert report.summary.total_predictions == 0
        assert report.summary.first_prediction_at is None
        assert report.summary.latest_prediction_at is None

    def test_empty_report_has_zero_data_statistics(self) -> None:
        report = ReportBuilder().build(user_id="user-0001", history=[])

        assert report.statistics.successful_predictions == 0
        assert report.statistics.partial_success_predictions == 0
        assert report.statistics.failed_predictions == 0
        assert report.statistics.average_confidence == 0.0
        assert report.statistics.average_agreement_ratio == 0.0
        assert report.statistics.most_predicted_class is None
        assert report.statistics.prediction_distribution == {}


class TestReportBuilderPopulatedHistory:
    """Verifies `ReportBuilder.build()` aggregation over a populated history collection."""

    def _build_sample_history(self) -> list:
        return [
            make_history_record(
                history_id="hist-0001",
                created_at="2026-07-27T10:00:00+00:00",
                status=PredictionHistoryStatus.SUCCESS,
                summary=make_summary(predicted_class="lung_aca", confidence=90.0, agreement_ratio=1.0),
            ),
            make_history_record(
                history_id="hist-0002",
                created_at="2026-07-28T10:00:00+00:00",
                status=PredictionHistoryStatus.PARTIAL_SUCCESS,
                summary=make_summary(predicted_class="lung_scc", confidence=70.0, agreement_ratio=0.5),
            ),
            make_history_record(
                history_id="hist-0003",
                created_at="2026-07-26T10:00:00+00:00",
                status=PredictionHistoryStatus.FAILED,
                summary=make_summary(predicted_class=None, confidence=0.0, agreement_ratio=0.0),
            ),
            make_history_record(
                history_id="hist-0004",
                created_at="2026-07-29T10:00:00+00:00",
                status=PredictionHistoryStatus.SUCCESS,
                summary=make_summary(predicted_class="lung_aca", confidence=80.0, agreement_ratio=1.0),
            ),
        ]

    def test_status_is_generated(self) -> None:
        report = ReportBuilder().build(user_id="user-0001", history=self._build_sample_history())

        assert report.status == ReportStatus.GENERATED

    def test_report_carries_the_original_history_collection(self) -> None:
        history = self._build_sample_history()

        report = ReportBuilder().build(user_id="user-0001", history=history)

        assert report.history == history

    def test_summary_counts_total_predictions(self) -> None:
        report = ReportBuilder().build(user_id="user-0001", history=self._build_sample_history())

        assert report.summary.total_predictions == 4

    def test_summary_derives_first_and_latest_prediction_regardless_of_input_order(self) -> None:
        report = ReportBuilder().build(user_id="user-0001", history=self._build_sample_history())

        assert report.summary.first_prediction_at == "2026-07-26T10:00:00+00:00"
        assert report.summary.latest_prediction_at == "2026-07-29T10:00:00+00:00"

    def test_statistics_count_each_status(self) -> None:
        report = ReportBuilder().build(user_id="user-0001", history=self._build_sample_history())

        assert report.statistics.successful_predictions == 2
        assert report.statistics.partial_success_predictions == 1
        assert report.statistics.failed_predictions == 1

    def test_statistics_average_confidence_excludes_records_without_a_predicted_class(self) -> None:
        report = ReportBuilder().build(user_id="user-0001", history=self._build_sample_history())

        # (90.0 + 70.0 + 80.0) / 3 == 80.0 -- the FAILED record (no predicted
        # class) must not be included in the average.
        assert report.statistics.average_confidence == 80.0

    def test_statistics_average_agreement_ratio_excludes_records_without_a_predicted_class(
        self,
    ) -> None:
        report = ReportBuilder().build(user_id="user-0001", history=self._build_sample_history())

        assert round(report.statistics.average_agreement_ratio, 4) == round((1.0 + 0.5 + 1.0) / 3, 4)

    def test_statistics_prediction_distribution_counts_per_class(self) -> None:
        report = ReportBuilder().build(user_id="user-0001", history=self._build_sample_history())

        assert report.statistics.prediction_distribution == {"lung_aca": 2, "lung_scc": 1}

    def test_statistics_most_predicted_class(self) -> None:
        report = ReportBuilder().build(user_id="user-0001", history=self._build_sample_history())

        assert report.statistics.most_predicted_class == "lung_aca"

    def test_each_build_call_produces_a_unique_report_id(self) -> None:
        builder = ReportBuilder()
        history = self._build_sample_history()

        first = builder.build(user_id="user-0001", history=history)
        second = builder.build(user_id="user-0001", history=history)

        assert first.report_id != second.report_id

    def test_never_mutates_the_supplied_history_records(self) -> None:
        history = self._build_sample_history()
        original_snapshot = [record.model_copy(deep=True) for record in history]

        ReportBuilder().build(user_id="user-0001", history=history)

        assert history == original_snapshot
