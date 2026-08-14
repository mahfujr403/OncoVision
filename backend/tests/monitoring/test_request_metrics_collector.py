"""Unit tests for `RequestMetricsCollector` (Phase 8.2, ADR-036).

Exercises the collector directly, with no FastAPI app, database, or AI
runtime involved -- mirroring how `tests/monitoring/test_monitoring_service.py`
unit-tests `MonitoringService` with lightweight fakes.
"""

from app.core.request_metrics import RequestMetricsCollector


class TestRecordRequest:
    def test_first_request_is_counted(self) -> None:
        collector = RequestMetricsCollector()

        collector.record_request(method="GET", path="/api/v1/health", status_code=200, duration_ms=10.0)
        snapshot = collector.snapshot()

        assert snapshot.total_requests == 1
        assert snapshot.status_2xx == 1
        assert snapshot.status_3xx == 0
        assert snapshot.status_4xx == 0
        assert snapshot.status_5xx == 0
        assert snapshot.average_duration_ms == 10.0

    def test_status_codes_are_bucketed_by_class(self) -> None:
        collector = RequestMetricsCollector()

        collector.record_request(method="GET", path="/x", status_code=200, duration_ms=1.0)
        collector.record_request(method="GET", path="/x", status_code=301, duration_ms=1.0)
        collector.record_request(method="GET", path="/x", status_code=404, duration_ms=1.0)
        collector.record_request(method="GET", path="/x", status_code=500, duration_ms=1.0)
        snapshot = collector.snapshot()

        assert snapshot.total_requests == 4
        assert snapshot.status_2xx == 1
        assert snapshot.status_3xx == 1
        assert snapshot.status_4xx == 1
        assert snapshot.status_5xx == 1

    def test_average_duration_is_computed_across_every_request(self) -> None:
        collector = RequestMetricsCollector()

        collector.record_request(method="GET", path="/x", status_code=200, duration_ms=10.0)
        collector.record_request(method="GET", path="/x", status_code=200, duration_ms=20.0)
        snapshot = collector.snapshot()

        assert snapshot.average_duration_ms == 15.0

    def test_average_duration_is_zero_when_no_requests_recorded(self) -> None:
        collector = RequestMetricsCollector()

        snapshot = collector.snapshot()

        assert snapshot.total_requests == 0
        assert snapshot.average_duration_ms == 0.0

    def test_negative_duration_is_clamped_to_zero_rather_than_corrupting_the_average(self) -> None:
        collector = RequestMetricsCollector()

        collector.record_request(method="GET", path="/x", status_code=200, duration_ms=-5.0)
        snapshot = collector.snapshot()

        assert snapshot.average_duration_ms == 0.0


class TestPredictionRequestTracking:
    def test_successful_prediction_request_is_counted(self) -> None:
        collector = RequestMetricsCollector()

        collector.record_request(
            method="POST", path="/api/v1/predictions", status_code=200, duration_ms=50.0
        )
        snapshot = collector.snapshot()

        assert snapshot.prediction_requests_total == 1
        assert snapshot.prediction_successful_total == 1
        assert snapshot.prediction_failed_total == 0

    def test_failed_prediction_request_is_counted(self) -> None:
        collector = RequestMetricsCollector()

        collector.record_request(
            method="POST", path="/api/v1/predictions", status_code=503, duration_ms=5.0
        )
        snapshot = collector.snapshot()

        assert snapshot.prediction_requests_total == 1
        assert snapshot.prediction_successful_total == 0
        assert snapshot.prediction_failed_total == 1

    def test_non_prediction_endpoints_are_not_counted_as_prediction_requests(self) -> None:
        collector = RequestMetricsCollector()

        collector.record_request(method="GET", path="/api/v1/health", status_code=200, duration_ms=1.0)
        collector.record_request(
            method="GET", path="/api/v1/predictions", status_code=200, duration_ms=1.0
        )
        collector.record_request(
            method="GET", path="/api/v1/history", status_code=200, duration_ms=1.0
        )
        snapshot = collector.snapshot()

        assert snapshot.total_requests == 3
        assert snapshot.prediction_requests_total == 0

    def test_prediction_path_prefix_match_is_not_counted(self) -> None:
        """`/api/v1/predictions/extra` must not be mistaken for the prediction endpoint."""
        collector = RequestMetricsCollector()

        collector.record_request(
            method="POST", path="/api/v1/predictions/extra", status_code=200, duration_ms=1.0
        )
        snapshot = collector.snapshot()

        assert snapshot.prediction_requests_total == 0


class TestReset:
    def test_reset_clears_all_counters(self) -> None:
        collector = RequestMetricsCollector()
        collector.record_request(
            method="POST", path="/api/v1/predictions", status_code=200, duration_ms=10.0
        )

        collector.reset()
        snapshot = collector.snapshot()

        assert snapshot.total_requests == 0
        assert snapshot.prediction_requests_total == 0
        assert snapshot.average_duration_ms == 0.0


class TestFailureIsolation:
    def test_record_request_never_raises_on_unexpected_status_code(self) -> None:
        collector = RequestMetricsCollector()

        # 999 is outside every recognized status class -- must be counted
        # in `total_requests` but not crash or misattribute a bucket.
        collector.record_request(method="GET", path="/x", status_code=999, duration_ms=1.0)
        snapshot = collector.snapshot()

        assert snapshot.total_requests == 1
        assert snapshot.status_2xx == 0
        assert snapshot.status_3xx == 0
        assert snapshot.status_4xx == 0
        assert snapshot.status_5xx == 0
