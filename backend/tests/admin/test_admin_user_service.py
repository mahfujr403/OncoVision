"""Unit tests for `AdminUserService` (Phase 7.2/7.3, ADR-036).

Exercises the service directly against `FakeUserRepository`/`FakeSession`
(`tests/admin/doubles.py`) -- no real database, mirroring how
`tests/history/test_prediction_history_service.py` exercises
`PredictionHistoryService` against an in-memory repository double.
"""

import asyncio
import uuid

import pytest

from app.admin.exceptions import (
    AdminUserNotFoundError,
    LastAdministratorProtectionError,
    SelfAccountStatusChangeError,
)
from app.history.pagination import PredictionHistoryPageRequest
from app.models.enums import UserRole
from app.services.admin_user_service import AdminUserService
from tests.admin.doubles import FakeSession, FakeUserRepository, make_user


def _service(users: list) -> tuple[AdminUserService, FakeSession]:
    session = FakeSession()
    service = AdminUserService(session=session, user_repository=FakeUserRepository(users))
    return service, session


class TestListUsers:
    def test_returns_page_of_users_and_metadata(self) -> None:
        users = [make_user(email=f"user{i}@example.com") for i in range(5)]
        service, _ = _service(users)

        async def run():
            return await service.list_users(
                PredictionHistoryPageRequest(page=1, page_size=2)
            )

        page_users, metadata = asyncio.run(run())

        assert len(page_users) == 2
        assert metadata.total_records == 5
        assert metadata.total_pages == 3


class TestGetUser:
    def test_returns_matching_user(self) -> None:
        target = make_user(email="target@example.com")
        service, _ = _service([target])

        result = asyncio.run(service.get_user(str(target.id)))

        assert result.id == target.id

    def test_nonexistent_user_raises_not_found(self) -> None:
        service, _ = _service([])

        with pytest.raises(AdminUserNotFoundError):
            asyncio.run(service.get_user(str(uuid.uuid4())))

    def test_malformed_user_id_raises_not_found(self) -> None:
        service, _ = _service([])

        with pytest.raises(AdminUserNotFoundError):
            asyncio.run(service.get_user("not-a-uuid"))


class TestActivateUser:
    def test_activates_inactive_user(self) -> None:
        target = make_user(is_active=False)
        service, session = _service([target])

        result = asyncio.run(service.activate_user(str(target.id)))

        assert result.is_active is True
        assert session.commit_count == 1

    def test_nonexistent_user_raises_not_found(self) -> None:
        service, _ = _service([])

        with pytest.raises(AdminUserNotFoundError):
            asyncio.run(service.activate_user(str(uuid.uuid4())))


class TestDeactivateUser:
    def test_deactivates_standard_user(self) -> None:
        admin = make_user(role=UserRole.ADMIN)
        target = make_user(role=UserRole.USER, is_active=True)
        service, session = _service([admin, target])

        result = asyncio.run(service.deactivate_user(str(target.id), acting_user=admin))

        assert result.is_active is False
        assert session.commit_count == 1

    def test_nonexistent_user_raises_not_found(self) -> None:
        admin = make_user(role=UserRole.ADMIN)
        service, _ = _service([admin])

        with pytest.raises(AdminUserNotFoundError):
            asyncio.run(service.deactivate_user(str(uuid.uuid4()), acting_user=admin))

    def test_self_deactivation_is_rejected(self) -> None:
        admin = make_user(role=UserRole.ADMIN)
        service, _ = _service([admin])

        with pytest.raises(SelfAccountStatusChangeError):
            asyncio.run(service.deactivate_user(str(admin.id), acting_user=admin))

    def test_last_active_administrator_is_protected(self) -> None:
        sole_admin = make_user(role=UserRole.ADMIN, email="sole-admin@example.com")
        # Router-level authorization (require_admin) always ensures the
        # actor is themselves an administrator; this unit test isolates
        # the service's own count-based protection logic by using a
        # distinct, non-admin actor so `sole_admin` is unambiguously the
        # only administrator in the fixture.
        other_actor = make_user(role=UserRole.USER, email="other-user@example.com")
        service, _ = _service([sole_admin, other_actor])

        with pytest.raises(LastAdministratorProtectionError):
            asyncio.run(service.deactivate_user(str(sole_admin.id), acting_user=other_actor))

    def test_deactivating_one_of_several_active_administrators_is_allowed(self) -> None:
        admin_one = make_user(role=UserRole.ADMIN, email="admin-one@example.com")
        admin_two = make_user(role=UserRole.ADMIN, email="admin-two@example.com")
        service, _ = _service([admin_one, admin_two])

        result = asyncio.run(service.deactivate_user(str(admin_one.id), acting_user=admin_two))

        assert result.is_active is False

    def test_deactivating_an_already_inactive_administrator_does_not_trigger_protection(
        self,
    ) -> None:
        acting_admin = make_user(role=UserRole.ADMIN, email="acting@example.com")
        already_inactive_admin = make_user(
            role=UserRole.ADMIN, is_active=False, email="inactive-admin@example.com"
        )
        service, _ = _service([acting_admin, already_inactive_admin])

        result = asyncio.run(
            service.deactivate_user(str(already_inactive_admin.id), acting_user=acting_admin)
        )

        assert result.is_active is False
