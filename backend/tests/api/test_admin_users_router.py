"""Router-level tests for `app.api.v1.admin.users` (Phase 7.1/7.2/7.3/7.6, ADR-036).

Exercises the Admin Users endpoints through the full FastAPI
routing/validation/exception-handling stack via
`fastapi.testclient.TestClient`, using `app.dependency_overrides` to
substitute the authenticated user (`get_current_active_user`) and the
Admin User Service (`get_admin_user_service`) -- the same
dependency-injection seams already used throughout `tests/api` -- so no
real database or JWT is required.

Also covers Phase 7.1's Admin Authorization Foundation matrix
(unauthenticated -> 401, authenticated non-admin -> 403, administrator ->
200) using this router as the concrete endpoint under test, since
`require_admin` itself is already exercised end-to-end this way.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.dependencies.auth import get_current_active_user
from app.dependencies.services import get_admin_user_service
from app.main import app
from app.models.enums import UserRole
from app.services.admin_user_service import AdminUserService
from tests.admin.doubles import FakeSession, FakeUserRepository, make_user

USERS_PATH = "/api/v1/admin/users"


@pytest.fixture
def admin_user():
    return make_user(role=UserRole.ADMIN, email="admin@example.com")


@pytest.fixture
def standard_user():
    return make_user(role=UserRole.USER, email="standard@example.com")


def _client_as(current_user, seed_users: list | None = None) -> TestClient:
    repository = FakeUserRepository(seed_users or [current_user])
    service = AdminUserService(session=FakeSession(), user_repository=repository)

    app.dependency_overrides[get_current_active_user] = lambda: current_user
    app.dependency_overrides[get_admin_user_service] = lambda: service

    return TestClient(app)


def _clear_overrides() -> None:
    app.dependency_overrides.pop(get_current_active_user, None)
    app.dependency_overrides.pop(get_admin_user_service, None)


class TestAdminAuthorizationFoundation:
    """Phase 7.1: ADMIN -> 200, NORMAL USER -> 403, UNAUTHENTICATED -> 401."""

    def test_unauthenticated_request_returns_401(self) -> None:
        # Deliberately no `get_current_active_user` override and no
        # Authorization header: `get_current_user` short-circuits with
        # `UnauthorizedError` before any service is ever reached.
        test_client = TestClient(app)

        response = test_client.get(USERS_PATH)

        assert response.status_code == 401

    def test_authenticated_non_admin_returns_403(self, standard_user) -> None:
        client = _client_as(standard_user)

        response = client.get(USERS_PATH)
        _clear_overrides()

        assert response.status_code == 403

    def test_administrator_returns_200(self, admin_user) -> None:
        client = _client_as(admin_user)

        response = client.get(USERS_PATH)
        _clear_overrides()

        assert response.status_code == 200
        assert response.json()["success"] is True


class TestListUsers:
    def test_returns_paginated_users(self, admin_user) -> None:
        other_users = [make_user(email=f"user{i}@example.com") for i in range(3)]
        client = _client_as(admin_user, seed_users=[admin_user, *other_users])

        response = client.get(USERS_PATH, params={"page": 1, "page_size": 2})
        _clear_overrides()

        assert response.status_code == 200
        payload = response.json()["data"]
        assert payload["count"] == 2
        assert payload["pagination"]["total_records"] == 4


class TestGetUser:
    def test_returns_user_detail(self, admin_user) -> None:
        target = make_user(email="target@example.com")
        client = _client_as(admin_user, seed_users=[admin_user, target])

        response = client.get(f"{USERS_PATH}/{target.id}")
        _clear_overrides()

        assert response.status_code == 200
        assert response.json()["data"]["email"] == "target@example.com"

    def test_nonexistent_user_returns_404(self, admin_user) -> None:
        client = _client_as(admin_user)

        response = client.get(f"{USERS_PATH}/{uuid.uuid4()}")
        _clear_overrides()

        assert response.status_code == 404

    def test_malformed_user_id_returns_404(self, admin_user) -> None:
        client = _client_as(admin_user)

        response = client.get(f"{USERS_PATH}/not-a-uuid")
        _clear_overrides()

        assert response.status_code == 404


class TestActivateUser:
    def test_activates_user_returns_200(self, admin_user) -> None:
        target = make_user(email="inactive@example.com", is_active=False)
        client = _client_as(admin_user, seed_users=[admin_user, target])

        response = client.post(f"{USERS_PATH}/{target.id}/activate")
        _clear_overrides()

        assert response.status_code == 200
        assert response.json()["data"]["user"]["is_active"] is True

    def test_nonexistent_user_returns_404(self, admin_user) -> None:
        client = _client_as(admin_user)

        response = client.post(f"{USERS_PATH}/{uuid.uuid4()}/activate")
        _clear_overrides()

        assert response.status_code == 404


class TestDeactivateUser:
    def test_deactivates_user_returns_200(self, admin_user) -> None:
        target = make_user(email="active@example.com", is_active=True)
        client = _client_as(admin_user, seed_users=[admin_user, target])

        response = client.post(f"{USERS_PATH}/{target.id}/deactivate")
        _clear_overrides()

        assert response.status_code == 200
        assert response.json()["data"]["user"]["is_active"] is False

    def test_nonexistent_user_returns_404(self, admin_user) -> None:
        client = _client_as(admin_user)

        response = client.post(f"{USERS_PATH}/{uuid.uuid4()}/deactivate")
        _clear_overrides()

        assert response.status_code == 404

    def test_self_deactivation_returns_400(self, admin_user) -> None:
        client = _client_as(admin_user, seed_users=[admin_user])

        response = client.post(f"{USERS_PATH}/{admin_user.id}/deactivate")
        _clear_overrides()

        assert response.status_code == 400

    def test_last_administrator_returns_409(self, admin_user) -> None:
        # `admin_user` is authenticated directly via a dependency override
        # (bypassing the real `get_current_active_user` active-status
        # check), so it can be marked inactive here without affecting
        # `require_admin` authorization -- isolating this scenario to
        # exactly one *active* administrator (`sole_target_admin`) in the
        # fixture, distinct from the acting user so the self-deactivation
        # guard (tested separately above) does not fire instead.
        inactive_acting_admin = make_user(
            role=UserRole.ADMIN, email="inactive-admin@example.com", is_active=False
        )
        sole_target_admin = make_user(role=UserRole.ADMIN, email="sole@example.com")
        client = _client_as(
            inactive_acting_admin, seed_users=[inactive_acting_admin, sole_target_admin]
        )

        response = client.post(f"{USERS_PATH}/{sole_target_admin.id}/deactivate")
        _clear_overrides()

        assert response.status_code == 409

    def test_invalid_user_id_format_is_handled_gracefully(self, admin_user) -> None:
        client = _client_as(admin_user)

        response = client.post(f"{USERS_PATH}/not-a-uuid/deactivate")
        _clear_overrides()

        assert response.status_code == 404
