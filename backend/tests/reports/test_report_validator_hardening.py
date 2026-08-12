"""Phase 6.6 Reporting Hardening unit tests for `ReportValidator.validate_export_limit()`."""

import pytest

from app.reports.exceptions import ReportExportLimitExceededError
from app.reports.validator import ReportValidator


class TestReportValidatorExportLimit:
    def test_raises_when_total_records_exceeds_max_rows(self) -> None:
        validator = ReportValidator()

        with pytest.raises(ReportExportLimitExceededError):
            validator.validate_export_limit(user_id="user-0001", total_records=1001, max_rows=1000)

    def test_does_not_raise_when_total_records_equals_max_rows(self) -> None:
        validator = ReportValidator()

        validator.validate_export_limit(user_id="user-0001", total_records=1000, max_rows=1000)

    def test_does_not_raise_when_total_records_is_below_max_rows(self) -> None:
        validator = ReportValidator()

        validator.validate_export_limit(user_id="user-0001", total_records=5, max_rows=1000)

    def test_does_not_raise_when_total_records_is_zero(self) -> None:
        validator = ReportValidator()

        validator.validate_export_limit(user_id="user-0001", total_records=0, max_rows=1000)
