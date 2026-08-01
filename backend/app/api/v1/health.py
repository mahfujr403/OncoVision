"""Health check endpoint.

Routers only receive requests and delegate to services; no business logic
lives here.
"""

from fastapi import APIRouter

from app.constants.app import TAG_HEALTH
from app.schemas.common import HealthStatus
from app.utils.response import success_response

router = APIRouter(tags=[TAG_HEALTH])


@router.get(
    "/health",
    summary="Health Check",
    description="Returns the current health status of the service.",
)
async def health_check():
    """Return a simple health status payload used for uptime checks."""
    health = HealthStatus(status="healthy")
    return success_response(
        data=health.model_dump(),
        message="Service is healthy.",
    )
