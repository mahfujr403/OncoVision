import logging
from fastapi import APIRouter, status

from app.constants.app import TAG_HEALTH
from app.database.database import check_readiness
from app.schemas.common import HealthStatus
from app.utils.response import error_response, success_response

logger = logging.getLogger(__name__)

router = APIRouter(tags=[TAG_HEALTH])


@router.get(
    "/health",
    summary="Health Check",
    description="Returns the current health status of the service (liveness probe).",
)
async def health_check():
    """Return a simple health status payload used for uptime checks."""
    health = HealthStatus(status="healthy")
    return success_response(
        data=health.model_dump(),
        message="Service is healthy.",
    )


@router.get(
    "/health/ready",
    summary="Readiness Check",
    description="Validates that database connectivity and pgvector are ready without calling external LLMs.",
)
async def readiness_check():
    """Verify application readiness for handling requests."""
    try:
        readiness_data = await check_readiness()
        return success_response(
            data={"status": "ready", **readiness_data},
            message="Service dependencies are ready.",
        )
    except Exception as e:
        logger.warning("Readiness check failed: %s", e)
        return error_response(
            message="Service dependencies are not ready.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            data={"status": "unready", "database": "disconnected"},
        )

