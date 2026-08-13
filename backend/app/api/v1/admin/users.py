"""Admin User Management endpoints (Phase 7.2/7.3/7.6, ADR-036).

Routers only receive requests and delegate to `AdminUserService`; no
business logic lives here, matching the convention already established
by `app.api.v1.history.router`. Every route requires administrative
authorization via `require_admin` (`app.dependencies.auth`):
unauthenticated callers receive `401`, authenticated non-administrators
receive `403`.

Exposes:

    GET  /api/v1/admin/users
    GET  /api/v1/admin/users/{user_id}
    POST /api/v1/admin/users/{user_id}/activate
    POST /api/v1/admin/users/{user_id}/deactivate
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from app.api.v1.admin.examples import (
    ADMIN_USER_NOT_FOUND_EXAMPLE,
    FORBIDDEN_ERROR_EXAMPLE,
    LAST_ADMINISTRATOR_PROTECTION_EXAMPLE,
    SELF_STATUS_CHANGE_ERROR_EXAMPLE,
)
from app.api.v1.predictions.examples import AUTHENTICATION_ERROR_EXAMPLE, INTERNAL_ERROR_EXAMPLE
from app.constants.app import TAG_ADMIN
from app.core.logging import get_logger
from app.dependencies.auth import require_admin
from app.dependencies.services import get_admin_user_service
from app.history.pagination import (
    DEFAULT_PAGE,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    MIN_PAGE_SIZE,
    PredictionHistoryPageRequest,
)
from app.models.user import User
from app.schemas.admin import (
    AdminPaginationSchema,
    AdminUserDetailResponseSchema,
    AdminUserListResponseSchema,
    AdminUserStatusChangeResponseSchema,
)
from app.schemas.response import APIResponse
from app.schemas.user import UserResponse
from app.services.admin_user_service import AdminUserService
from app.utils.response import success_response

logger = get_logger(__name__)

router = APIRouter(prefix="/users", tags=[TAG_ADMIN])


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="List registered users",
    description=(
        "Returns one page of registered users, newest first. "
        "Administrator authorization is required."
    ),
    response_model=APIResponse[AdminUserListResponseSchema],
    responses={
        200: {"description": "A page of registered users was retrieved."},
        401: {
            "description": "Missing or invalid authentication credentials.",
            "content": {"application/json": {"example": AUTHENTICATION_ERROR_EXAMPLE}},
        },
        403: {
            "description": "The authenticated user is not an administrator.",
            "content": {"application/json": {"example": FORBIDDEN_ERROR_EXAMPLE}},
        },
        500: {
            "description": "An unexpected internal server error occurred.",
            "content": {"application/json": {"example": INTERNAL_ERROR_EXAMPLE}},
        },
    },
)
async def list_users(
    _admin: Annotated[User, Depends(require_admin)],
    admin_user_service: Annotated[AdminUserService, Depends(get_admin_user_service)],
    page: Annotated[
        int, Query(ge=1, description="1-indexed page number to retrieve.")
    ] = DEFAULT_PAGE,
    page_size: Annotated[
        int,
        Query(
            ge=MIN_PAGE_SIZE,
            le=MAX_PAGE_SIZE,
            description="Maximum number of records to return for this page.",
        ),
    ] = DEFAULT_PAGE_SIZE,
):
    """Return one page of registered users, newest first."""
    page_request = PredictionHistoryPageRequest(page=page, page_size=page_size)

    logger.info(
        "Admin user list requested: page=%d page_size=%d", page_request.page, page_request.page_size
    )

    users, metadata = await admin_user_service.list_users(page_request=page_request)

    items = [UserResponse.model_validate(user) for user in users]
    response_data = AdminUserListResponseSchema(
        items=items,
        count=len(items),
        pagination=AdminPaginationSchema(**metadata.model_dump()),
    )

    return success_response(
        data=response_data.model_dump(mode="json"),
        message="Users retrieved successfully.",
    )


@router.get(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Retrieve a single user",
    description="Returns the complete profile of a single registered user by ID.",
    response_model=APIResponse[AdminUserDetailResponseSchema],
    responses={
        200: {"description": "The requested user was retrieved."},
        401: {
            "description": "Missing or invalid authentication credentials.",
            "content": {"application/json": {"example": AUTHENTICATION_ERROR_EXAMPLE}},
        },
        403: {
            "description": "The authenticated user is not an administrator.",
            "content": {"application/json": {"example": FORBIDDEN_ERROR_EXAMPLE}},
        },
        404: {
            "description": "No user matches `user_id`.",
            "content": {"application/json": {"example": ADMIN_USER_NOT_FOUND_EXAMPLE}},
        },
        500: {
            "description": "An unexpected internal server error occurred.",
            "content": {"application/json": {"example": INTERNAL_ERROR_EXAMPLE}},
        },
    },
)
async def get_user(
    _admin: Annotated[User, Depends(require_admin)],
    admin_user_service: Annotated[AdminUserService, Depends(get_admin_user_service)],
    user_id: Annotated[str, Path(description="Unique identifier of the user to retrieve.")],
):
    """Return the complete profile of a single registered user."""
    logger.info("Admin user detail requested: user_id=%s", user_id)

    user = await admin_user_service.get_user(user_id=user_id)

    return success_response(
        data=UserResponse.model_validate(user).model_dump(mode="json"),
        message="User retrieved successfully.",
    )


@router.post(
    "/{user_id}/activate",
    status_code=status.HTTP_200_OK,
    summary="Activate a user account",
    description="Sets the target user's `is_active` flag to `true`.",
    response_model=APIResponse[AdminUserStatusChangeResponseSchema],
    responses={
        200: {"description": "The user account was activated."},
        401: {
            "description": "Missing or invalid authentication credentials.",
            "content": {"application/json": {"example": AUTHENTICATION_ERROR_EXAMPLE}},
        },
        403: {
            "description": "The authenticated user is not an administrator.",
            "content": {"application/json": {"example": FORBIDDEN_ERROR_EXAMPLE}},
        },
        404: {
            "description": "No user matches `user_id`.",
            "content": {"application/json": {"example": ADMIN_USER_NOT_FOUND_EXAMPLE}},
        },
        500: {
            "description": "An unexpected internal server error occurred.",
            "content": {"application/json": {"example": INTERNAL_ERROR_EXAMPLE}},
        },
    },
)
async def activate_user(
    _admin: Annotated[User, Depends(require_admin)],
    admin_user_service: Annotated[AdminUserService, Depends(get_admin_user_service)],
    user_id: Annotated[str, Path(description="Unique identifier of the user to activate.")],
):
    """Activate a user account."""
    logger.info("Admin user activation requested: user_id=%s", user_id)

    user = await admin_user_service.activate_user(user_id=user_id)

    response_data = AdminUserStatusChangeResponseSchema(user=UserResponse.model_validate(user))
    return success_response(
        data=response_data.model_dump(mode="json"),
        message="User activated successfully.",
    )


@router.post(
    "/{user_id}/deactivate",
    status_code=status.HTTP_200_OK,
    summary="Deactivate a user account",
    description=(
        "Sets the target user's `is_active` flag to `false`. An "
        "administrator may not deactivate their own account, and the "
        "last remaining active administrator account cannot be deactivated."
    ),
    response_model=APIResponse[AdminUserStatusChangeResponseSchema],
    responses={
        200: {"description": "The user account was deactivated."},
        400: {
            "description": "The authenticated administrator attempted to deactivate their own account.",
            "content": {"application/json": {"example": SELF_STATUS_CHANGE_ERROR_EXAMPLE}},
        },
        401: {
            "description": "Missing or invalid authentication credentials.",
            "content": {"application/json": {"example": AUTHENTICATION_ERROR_EXAMPLE}},
        },
        403: {
            "description": "The authenticated user is not an administrator.",
            "content": {"application/json": {"example": FORBIDDEN_ERROR_EXAMPLE}},
        },
        404: {
            "description": "No user matches `user_id`.",
            "content": {"application/json": {"example": ADMIN_USER_NOT_FOUND_EXAMPLE}},
        },
        409: {
            "description": "Deactivating this user would leave no active administrator accounts.",
            "content": {
                "application/json": {"example": LAST_ADMINISTRATOR_PROTECTION_EXAMPLE}
            },
        },
        500: {
            "description": "An unexpected internal server error occurred.",
            "content": {"application/json": {"example": INTERNAL_ERROR_EXAMPLE}},
        },
    },
)
async def deactivate_user(
    admin: Annotated[User, Depends(require_admin)],
    admin_user_service: Annotated[AdminUserService, Depends(get_admin_user_service)],
    user_id: Annotated[str, Path(description="Unique identifier of the user to deactivate.")],
):
    """Deactivate a user account."""
    logger.info("Admin user deactivation requested: user_id=%s by=%s", user_id, admin.id)

    user = await admin_user_service.deactivate_user(user_id=user_id, acting_user=admin)

    response_data = AdminUserStatusChangeResponseSchema(user=UserResponse.model_validate(user))
    return success_response(
        data=response_data.model_dump(mode="json"),
        message="User deactivated successfully.",
    )
