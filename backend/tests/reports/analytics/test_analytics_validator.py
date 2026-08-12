"""Tests for `AnalyticsValidator` (Phase 6.2, ADR-038)."""

import pytest

from app.reports.analytics.exceptions import InvalidAnalyticsRequestError
from app.reports.analytics.analytics_validator import AnalyticsValidator


class TestAnalyticsValidator:
    """Verifies `AnalyticsValidator.validate()`'s own, non-duplicated responsibilities."""

    def test_valid_user_id_does_not_raise(self) -> None:
        AnalyticsValidator().validate(user_id="user-0001")

    def test_missing_user_id_raises(self) -> None:
        with pytest.raises(InvalidAnalyticsRequestError):
            AnalyticsValidator().validate(user_id="")

    def test_blank_user_id_raises(self) -> None:
        with pytest.raises(InvalidAnalyticsRequestError):
            AnalyticsValidator().validate(user_id="   ")

    def test_none_user_id_raises(self) -> None:
        with pytest.raises(InvalidAnalyticsRequestError):
            AnalyticsValidator().validate(user_id=None)  # type: ignore[arg-type]
