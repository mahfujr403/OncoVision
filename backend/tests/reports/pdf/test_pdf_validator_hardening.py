"""Phase 6.6 Reporting Hardening unit tests for `PDFValidator`'s export safeguards."""

import pytest

from app.reports.pdf.exceptions import PDFExportLimitExceededError
from app.reports.pdf.pdf_validator import PDFValidator


class TestPDFValidatorExportLimit:
    def test_raises_when_total_records_exceeds_max_rows(self) -> None:
        validator = PDFValidator()

        with pytest.raises(PDFExportLimitExceededError):
            validator.validate_export_limit(user_id="user-0001", total_records=1001, max_rows=1000)

    def test_does_not_raise_when_total_records_equals_max_rows(self) -> None:
        validator = PDFValidator()

        validator.validate_export_limit(user_id="user-0001", total_records=1000, max_rows=1000)

    def test_does_not_raise_when_total_records_is_below_max_rows(self) -> None:
        validator = PDFValidator()

        validator.validate_export_limit(user_id="user-0001", total_records=5, max_rows=1000)


class TestPDFValidatorExportSize:
    def test_raises_when_content_size_exceeds_max_size(self) -> None:
        validator = PDFValidator()

        with pytest.raises(PDFExportLimitExceededError):
            validator.validate_export_size(
                user_id="user-0001", content_size_bytes=5_000_001, max_size_bytes=5_000_000
            )

    def test_does_not_raise_when_content_size_equals_max_size(self) -> None:
        validator = PDFValidator()

        validator.validate_export_size(
            user_id="user-0001", content_size_bytes=5_000_000, max_size_bytes=5_000_000
        )

    def test_does_not_raise_when_content_size_is_below_max_size(self) -> None:
        validator = PDFValidator()

        validator.validate_export_size(
            user_id="user-0001", content_size_bytes=120, max_size_bytes=5_000_000
        )
