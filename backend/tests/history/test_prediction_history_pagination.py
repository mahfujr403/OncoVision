"""Tests for Phase 5.4 Prediction History Pagination & Filtering (ADR-035).

Covers what this phase introduces on top of Phase 5.1-5.3:
    - `PredictionHistoryFilter` -- optional filter criteria with cross-field
      range validation and the `is_empty` property.
    - `PredictionHistoryPageRequest` -- validated `page`/`page_size` with
      `limit`/`offset` derivation.
    - `PredictionHistoryPageMetadata.from_totals()` -- pagination metadata
      arithmetic.
    - `SQLAlchemyPredictionHistoryRepository.count_by_user()` -- exercised
      against a lightweight fake `AsyncSession`, mirroring the
      `list_by_user()` test pattern already used in
      `test_prediction_history_retrieval.py`.
    - `PredictionHistoryRepository.list_by_user()` / `.count_by_user()`
      applying `filters` -- verified against the in-memory fake's
      filtering semantics (`InMemoryPredictionHistoryRepository`), since
      that keeps this suite consistent with the rest of the Phase 5.x
      test style rather than introducing SQL statement introspection.
    - `PredictionHistoryService.list_history_page()` -- delegates to
      `list_by_user()` + `count_by_user()`, never returns another user's
      records, and passes `filters` straight through unchanged.
"""

import asyncio
import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.history.enums import PredictionHistoryStatus
from app.history.filters import PredictionHistoryFilter
from app.history.metadata import PredictionHistoryMetadata
from app.history.pagination import (
    PredictionHistoryPage,
    PredictionHistoryPageMetadata,
    PredictionHistoryPageRequest,
)
from app.history.prediction_history import PredictionHistory
from app.history.summary import PredictionHistorySummary
from app.repositories.prediction_history_repository import SQLAlchemyPredictionHistoryRepository
from app.services.prediction_history_service import PredictionHistoryService
from tests.history.conftest_helpers import make_context
from tests.history.test_prediction_history_repository import InMemoryPredictionHistoryRepository


def _make_history(
    user_id: str,
    history_id: str,
    created_at: str,
    predicted_class: str = "lung_aca",
    confidence: float = 91.2,
    status_value: PredictionHistoryStatus = PredictionHistoryStatus.SUCCESS,
) -> PredictionHistory:
    """Build a domain-level `PredictionHistory` directly, avoiding a full mapper round-trip."""
    context = make_context(user_id=user_id)
    metadata = PredictionHistoryMetadata(
        request_id=context.request_id,
        requested_at=context.requested_at,
        user_id=user_id,
        user_email=context.user_email,
        image_filename=context.image_filename,
        image_content_type=context.image_content_type,
        image_size_bytes=context.image_size_bytes,
        image_width=context.image_width,
        image_height=context.image_height,
    )
    summary = PredictionHistorySummary(
        predicted_class=predicted_class,
        confidence=confidence,
        agreement_ratio=1.0,
        successful_models=["mobilenetv2"],
        failed_models=[],
        participating_models=1,
        individual_predictions=[],
    )
    return PredictionHistory(
        history_id=history_id,
        request_id=context.request_id,
        user_id=user_id,
        status=status_value,
        created_at=created_at,
        metadata=metadata,
        summary=summary,
    )


class TestPredictionHistoryFilter:
    """Verifies `PredictionHistoryFilter` (Phase 5.4, ADR-035)."""

    def test_constructs_successfully_with_all_fields_none(self) -> None:
        filters = PredictionHistoryFilter()

        assert filters.is_empty is True

    def test_constructs_successfully_with_a_valid_range(self) -> None:
        filters = PredictionHistoryFilter(
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 1, 31, tzinfo=timezone.utc),
            min_confidence=50.0,
            max_confidence=90.0,
        )

        assert filters.is_empty is False

    def test_raises_when_start_date_after_end_date(self) -> None:
        with pytest.raises(ValidationError):
            PredictionHistoryFilter(
                start_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
                end_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )

    def test_raises_when_min_confidence_greater_than_max_confidence(self) -> None:
        with pytest.raises(ValidationError):
            PredictionHistoryFilter(min_confidence=90.0, max_confidence=10.0)

    @pytest.mark.parametrize(
        "overrides",
        [
            {"status": PredictionHistoryStatus.SUCCESS},
            {"predicted_class": "lung_aca"},
            {"start_date": datetime(2026, 1, 1, tzinfo=timezone.utc)},
            {"end_date": datetime(2026, 1, 1, tzinfo=timezone.utc)},
            {"min_confidence": 50.0},
            {"max_confidence": 90.0},
        ],
    )
    def test_is_empty_is_false_when_any_single_field_is_set(self, overrides: dict) -> None:
        filters = PredictionHistoryFilter(**overrides)

        assert filters.is_empty is False


class TestPredictionHistoryPageRequest:
    """Verifies `PredictionHistoryPageRequest` (Phase 5.4, ADR-035)."""

    def test_defaults_to_page_1_page_size_20(self) -> None:
        page_request = PredictionHistoryPageRequest()

        assert page_request.page == 1
        assert page_request.page_size == 20

    @pytest.mark.parametrize(
        "page,page_size,expected_offset",
        [
            (1, 20, 0),
            (2, 20, 20),
            (3, 10, 20),
            (1, 100, 0),
            (5, 1, 4),
        ],
    )
    def test_limit_and_offset_compute_correctly(
        self, page: int, page_size: int, expected_offset: int
    ) -> None:
        page_request = PredictionHistoryPageRequest(page=page, page_size=page_size)

        assert page_request.limit == page_size
        assert page_request.offset == expected_offset

    def test_rejects_page_zero(self) -> None:
        with pytest.raises(ValidationError):
            PredictionHistoryPageRequest(page=0)

    def test_rejects_page_size_zero(self) -> None:
        with pytest.raises(ValidationError):
            PredictionHistoryPageRequest(page_size=0)

    def test_rejects_page_size_above_maximum(self) -> None:
        with pytest.raises(ValidationError):
            PredictionHistoryPageRequest(page_size=101)


class TestPredictionHistoryPageMetadataFromTotals:
    """Verifies `PredictionHistoryPageMetadata.from_totals()` (Phase 5.4, ADR-035)."""

    def test_zero_total_records(self) -> None:
        page_request = PredictionHistoryPageRequest(page=1, page_size=20)

        metadata = PredictionHistoryPageMetadata.from_totals(page_request, total_records=0)

        assert metadata.total_pages == 0
        assert metadata.has_next is False
        assert metadata.has_previous is False

    def test_total_records_exactly_divisible_by_page_size(self) -> None:
        page_request = PredictionHistoryPageRequest(page=1, page_size=10)

        metadata = PredictionHistoryPageMetadata.from_totals(page_request, total_records=20)

        assert metadata.total_pages == 2

    def test_total_records_not_evenly_divisible_by_page_size(self) -> None:
        page_request = PredictionHistoryPageRequest(page=1, page_size=10)

        metadata = PredictionHistoryPageMetadata.from_totals(page_request, total_records=21)

        assert metadata.total_pages == 3

    def test_first_page_has_next_but_not_previous(self) -> None:
        page_request = PredictionHistoryPageRequest(page=1, page_size=10)

        metadata = PredictionHistoryPageMetadata.from_totals(page_request, total_records=25)

        assert metadata.has_next is True
        assert metadata.has_previous is False

    def test_middle_page_has_next_and_previous(self) -> None:
        page_request = PredictionHistoryPageRequest(page=2, page_size=10)

        metadata = PredictionHistoryPageMetadata.from_totals(page_request, total_records=25)

        assert metadata.has_next is True
        assert metadata.has_previous is True

    def test_last_page_has_previous_but_not_next(self) -> None:
        page_request = PredictionHistoryPageRequest(page=3, page_size=10)

        metadata = PredictionHistoryPageMetadata.from_totals(page_request, total_records=25)

        assert metadata.has_next is False
        assert metadata.has_previous is True


class _FakeScalarResult:
    def __init__(self, value: int) -> None:
        self._value = value

    def scalar_one(self) -> int:
        return self._value


class _FakeAsyncSessionForCount:
    """Minimal `AsyncSession` stand-in shaped for `count_by_user()`.

    Distinct from `_FakeAsyncSession` in `test_prediction_history_retrieval.py`,
    which is shaped for `list_by_user()`'s `.scalars().all()` access
    pattern -- `count_by_user()` calls `.scalar_one()` directly on the
    execute result instead.
    """

    def __init__(self, total: int) -> None:
        self._total = total
        self.executed_statements: list = []

    async def execute(self, statement):
        self.executed_statements.append(statement)
        return _FakeScalarResult(self._total)


class TestSQLAlchemyPredictionHistoryRepositoryCountByUser:
    """Verifies `SQLAlchemyPredictionHistoryRepository.count_by_user()` (Phase 5.4, ADR-035)."""

    def test_count_by_user_returns_the_preset_total(self) -> None:
        session = _FakeAsyncSessionForCount(total=7)
        repository = SQLAlchemyPredictionHistoryRepository(session)

        total = asyncio.run(repository.count_by_user(user_id=str(uuid.uuid4())))

        assert total == 7
        assert len(session.executed_statements) == 1

    def test_count_by_user_returns_zero_for_malformed_user_id(self) -> None:
        session = _FakeAsyncSessionForCount(total=99)
        repository = SQLAlchemyPredictionHistoryRepository(session)

        total = asyncio.run(repository.count_by_user(user_id="not-a-uuid"))

        assert total == 0
        # The malformed identifier must be rejected before any query runs.
        assert session.executed_statements == []

    def test_count_by_user_applies_filters_without_error(self) -> None:
        session = _FakeAsyncSessionForCount(total=3)
        repository = SQLAlchemyPredictionHistoryRepository(session)
        filters = PredictionHistoryFilter(status=PredictionHistoryStatus.SUCCESS)

        total = asyncio.run(
            repository.count_by_user(user_id=str(uuid.uuid4()), filters=filters)
        )

        assert total == 3
        assert len(session.executed_statements) == 1


class TestInMemoryRepositoryFiltering:
    """Verifies `list_by_user()`/`count_by_user()` apply `filters` (Phase 5.4, ADR-035).

    Exercised against `InMemoryPredictionHistoryRepository`, which
    implements the exact same filtering semantics as
    `SQLAlchemyPredictionHistoryRepository._apply_filters()` -- consistent
    with this codebase's existing preference (see
    `test_prediction_history_retrieval.py`) for lightweight fakes over SQL
    statement introspection.
    """

    def test_status_filter_narrows_results(self) -> None:
        repository = InMemoryPredictionHistoryRepository()
        owner_id = "user-0001"
        success_record = _make_history(
            owner_id, "hist-1", "2026-07-27T10:00:00+00:00", status_value=PredictionHistoryStatus.SUCCESS
        )
        failed_record = _make_history(
            owner_id, "hist-2", "2026-07-27T11:00:00+00:00", status_value=PredictionHistoryStatus.FAILED
        )

        async def scenario() -> list[PredictionHistory]:
            await repository.save(success_record)
            await repository.save(failed_record)
            return await repository.list_by_user(
                user_id=owner_id,
                limit=10,
                offset=0,
                filters=PredictionHistoryFilter(status=PredictionHistoryStatus.SUCCESS),
            )

        results = asyncio.run(scenario())

        assert results == [success_record]

    def test_confidence_range_filter_narrows_results(self) -> None:
        repository = InMemoryPredictionHistoryRepository()
        owner_id = "user-0001"
        low = _make_history(owner_id, "hist-1", "2026-07-27T10:00:00+00:00", confidence=40.0)
        high = _make_history(owner_id, "hist-2", "2026-07-27T11:00:00+00:00", confidence=95.0)

        async def scenario() -> list[PredictionHistory]:
            await repository.save(low)
            await repository.save(high)
            return await repository.list_by_user(
                user_id=owner_id,
                limit=10,
                offset=0,
                filters=PredictionHistoryFilter(min_confidence=90.0),
            )

        results = asyncio.run(scenario())

        assert results == [high]

    def test_date_range_filter_is_inclusive(self) -> None:
        repository = InMemoryPredictionHistoryRepository()
        owner_id = "user-0001"
        record = _make_history(owner_id, "hist-1", "2026-07-27T10:00:00+00:00")

        async def scenario() -> list[PredictionHistory]:
            await repository.save(record)
            return await repository.list_by_user(
                user_id=owner_id,
                limit=10,
                offset=0,
                filters=PredictionHistoryFilter(
                    start_date=datetime(2026, 7, 27, 10, 0, tzinfo=timezone.utc),
                    end_date=datetime(2026, 7, 27, 10, 0, tzinfo=timezone.utc),
                ),
            )

        results = asyncio.run(scenario())

        assert results == [record]

    def test_count_by_user_matches_list_by_user_for_the_same_filters(self) -> None:
        repository = InMemoryPredictionHistoryRepository()
        owner_id = "user-0001"
        matching = _make_history(
            owner_id, "hist-1", "2026-07-27T10:00:00+00:00", predicted_class="lung_aca"
        )
        non_matching = _make_history(
            owner_id, "hist-2", "2026-07-27T11:00:00+00:00", predicted_class="lung_n"
        )
        filters = PredictionHistoryFilter(predicted_class="lung_aca")

        async def scenario() -> tuple[list[PredictionHistory], int]:
            await repository.save(matching)
            await repository.save(non_matching)
            items = await repository.list_by_user(
                user_id=owner_id, limit=10, offset=0, filters=filters
            )
            total = await repository.count_by_user(user_id=owner_id, filters=filters)
            return items, total

        items, total = asyncio.run(scenario())

        assert items == [matching]
        assert total == 1


class TestPredictionHistoryServiceListHistoryPage:
    """Verifies `PredictionHistoryService.list_history_page()` (Phase 5.4, ADR-035)."""

    def test_delegates_to_repository_and_returns_a_correct_page(self) -> None:
        repository = InMemoryPredictionHistoryRepository()
        service = PredictionHistoryService(repository=repository)
        owner_id = "user-0001"
        first = _make_history(owner_id, "hist-1", "2026-07-27T09:00:00+00:00")
        second = _make_history(owner_id, "hist-2", "2026-07-27T10:00:00+00:00")

        async def scenario() -> PredictionHistoryPage:
            await repository.save(first)
            await repository.save(second)
            return await service.list_history_page(
                user_id=owner_id,
                page_request=PredictionHistoryPageRequest(page=1, page_size=20),
            )

        page = asyncio.run(scenario())

        assert isinstance(page, PredictionHistoryPage)
        assert len(page.items) == 2
        assert page.metadata.total_records == 2
        assert page.metadata.total_pages == 1

    def test_never_returns_another_users_records(self) -> None:
        repository = InMemoryPredictionHistoryRepository()
        service = PredictionHistoryService(repository=repository)

        async def scenario() -> PredictionHistoryPage:
            return await service.list_history_page(
                user_id="someone-else",
                page_request=PredictionHistoryPageRequest(),
            )

        page = asyncio.run(scenario())

        assert page.items == []
        assert page.metadata.total_records == 0

    def test_passes_filters_straight_through_to_the_repository(self) -> None:
        class TrackingRepository(InMemoryPredictionHistoryRepository):
            def __init__(self) -> None:
                super().__init__()
                self.received_filters: list[PredictionHistoryFilter | None] = []

            async def list_by_user(
                self, user_id: str, limit: int, offset: int, filters=None
            ) -> list[PredictionHistory]:
                self.received_filters.append(filters)
                return await super().list_by_user(user_id, limit, offset, filters)

            async def count_by_user(self, user_id: str, filters=None) -> int:
                self.received_filters.append(filters)
                return await super().count_by_user(user_id, filters)

        repository = TrackingRepository()
        service = PredictionHistoryService(repository=repository)
        filters = PredictionHistoryFilter(status=PredictionHistoryStatus.SUCCESS)

        async def scenario() -> None:
            await service.list_history_page(
                user_id="user-0001",
                page_request=PredictionHistoryPageRequest(),
                filters=filters,
            )

        asyncio.run(scenario())

        assert repository.received_filters == [filters, filters]
