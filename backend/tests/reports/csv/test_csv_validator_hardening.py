"""Phase 6.6 Reporting Hardening unit tests for `CSVValidator`'s export safeguards."""

import pytest

from app.reports.csv.csv_validator import CSVValidator
from app.reports.csv.exceptions import CSVExportLimitExceededError


class TestCSVValidatorExportLimit:
    def test_raises_when_total_records_exceeds_max_rows(self) -> None:
        validator = CSVValidator()

        with pytest.raises(CSVExportLimitExceededError):
            validator.validate_export_limit(user_id="user-0001", total_records=1001, max_rows=1000)

    def test_does_not_raise_when_total_records_equals_max_rows(self) -> None:
        validator = CSVValidator()

        validator.validate_export_limit(user_id="user-0001", total_records=1000, max_rows=1000)

    def test_does_not_raise_when_total_records_is_below_max_rows(self) -> None:
        validator = CSVValidator()

        validator.validate_export_limit(user_id="user-0001", total_records=5, max_rows=1000)


class TestCSVValidatorExportSize:
    def test_raises_when_content_size_exceeds_max_size(self) -> None:
        validator = CSVValidator()

        with pytest.raises(CSVExportLimitExceededError):
            validator.validate_export_size(
                user_id="user-0001", content_size_bytes=5_000_001, max_size_bytes=5_000_000
            )

    def test_does_not_raise_when_content_size_equals_max_size(self) -> None:
        validator = CSVValidator()

        validator.validate_export_size(
            user_id="user-0001", content_size_bytes=5_000_000, max_size_bytes=5_000_000
        )

    def test_does_not_raise_when_content_size_is_below_max_size(self) -> None:
        validator = CSVValidator()

        validator.validate_export_size(
            user_id="user-0001", content_size_bytes=120, max_size_bytes=5_000_000
        )
