"""Tests for `ReportValidator` (Phase 6.1, ADR-037)."""

import pytest

from app.reports.exceptions import InvalidReportRequestError
from app.reports.validator import ReportValidator
from app.schemas.report import ReportRequest


class TestReportValidator:
    """Verifies `ReportValidator.validate()`'s own, non-duplicated responsibilities."""

    def test_valid_request_does_not_raise(self) -> None:
        ReportValidator().validate(user_id="user-0001", request=ReportRequest())

    def test_missing_user_id_raises(self) -> None:
        with pytest.raises(InvalidReportRequestError):
            ReportValidator().validate(user_id="", request=ReportRequest())

    def test_blank_user_id_raises(self) -> None:
        with pytest.raises(InvalidReportRequestError):
            ReportValidator().validate(user_id="   ", request=ReportRequest())

    def test_none_user_id_raises(self) -> None:
        with pytest.raises(InvalidReportRequestError):
            ReportValidator().validate(user_id=None, request=ReportRequest())  # type: ignore[arg-type]

    def test_request_with_filters_does_not_raise(self) -> None:
        from app.history.filters import PredictionHistoryFilter

        request = ReportRequest(filters=PredictionHistoryFilter())

        ReportValidator().validate(user_id="user-0001", request=request)
