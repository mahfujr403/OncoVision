"""Tests for `CSVValidator` (Phase 6.3, ADR-039)."""

import pytest

from app.reports.csv.csv_validator import CSVValidator
from app.reports.csv.exceptions import InvalidCSVExportRequestError
from tests.reports.conftest_helpers import make_history_record


class TestCSVValidatorUserId:
    """Verifies `CSVValidator.validate()`'s own, non-duplicated responsibilities."""

    def test_valid_user_id_does_not_raise(self) -> None:
        CSVValidator().validate(user_id="user-0001")

    def test_missing_user_id_raises(self) -> None:
        with pytest.raises(InvalidCSVExportRequestError):
            CSVValidator().validate(user_id="")

    def test_blank_user_id_raises(self) -> None:
        with pytest.raises(InvalidCSVExportRequestError):
            CSVValidator().validate(user_id="   ")

    def test_none_user_id_raises(self) -> None:
        with pytest.raises(InvalidCSVExportRequestError):
            CSVValidator().validate(user_id=None)  # type: ignore[arg-type]


class TestCSVValidatorNoteIfEmpty:
    """Verifies `CSVValidator.note_if_empty()` never raises regardless of input."""

    def test_empty_history_does_not_raise(self) -> None:
        CSVValidator().note_if_empty(user_id="user-0001", history=[])

    def test_populated_history_does_not_raise(self) -> None:
        CSVValidator().note_if_empty(user_id="user-0001", history=[make_history_record()])
