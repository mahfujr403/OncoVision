"""Tests for `PDFValidator` (Phase 6.4, ADR-040)."""

import pytest

from app.reports.pdf.enums import PDFPageSize
from app.reports.pdf.exceptions import InvalidPDFExportRequestError
from app.reports.pdf.pdf_validator import PDFValidator
from tests.reports.conftest_helpers import make_history_record


class TestPDFValidatorUserId:
    """Verifies `PDFValidator.validate()`'s own, non-duplicated responsibilities."""

    def test_valid_request_does_not_raise(self) -> None:
        PDFValidator().validate(user_id="user-0001")

    def test_missing_user_id_raises(self) -> None:
        with pytest.raises(InvalidPDFExportRequestError):
            PDFValidator().validate(user_id="")

    def test_blank_user_id_raises(self) -> None:
        with pytest.raises(InvalidPDFExportRequestError):
            PDFValidator().validate(user_id="   ")

    def test_none_user_id_raises(self) -> None:
        with pytest.raises(InvalidPDFExportRequestError):
            PDFValidator().validate(user_id=None)  # type: ignore[arg-type]


class TestPDFValidatorPageSize:
    """Verifies `PDFValidator.validate()` rejects unsupported page-size options."""

    def test_default_page_size_is_a4_and_does_not_raise(self) -> None:
        PDFValidator().validate(user_id="user-0001")

    def test_explicit_a4_does_not_raise(self) -> None:
        PDFValidator().validate(user_id="user-0001", page_size=PDFPageSize.A4)

    def test_non_enum_page_size_raises(self) -> None:
        with pytest.raises(InvalidPDFExportRequestError):
            PDFValidator().validate(user_id="user-0001", page_size="letter")  # type: ignore[arg-type]

    def test_none_page_size_raises(self) -> None:
        with pytest.raises(InvalidPDFExportRequestError):
            PDFValidator().validate(user_id="user-0001", page_size=None)  # type: ignore[arg-type]


class TestPDFValidatorNoteIfEmpty:
    """Verifies `PDFValidator.note_if_empty()` never raises regardless of input."""

    def test_empty_history_does_not_raise(self) -> None:
        PDFValidator().note_if_empty(user_id="user-0001", history=[])

    def test_populated_history_does_not_raise(self) -> None:
        PDFValidator().note_if_empty(user_id="user-0001", history=[make_history_record()])
