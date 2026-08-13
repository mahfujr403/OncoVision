"""Admin System & Runtime Administration Service (Phase 7.5, ADR-036).

`AdminSystemService` aggregates existing, already-safe operational
metadata into a single administrative status snapshot. It introduces no
second runtime manager and performs no TensorFlow/database access of its
own -- every value is sourced from components that already exist and are
already exposed, in the same shape, by the self-service `/system/*`
endpoints (`app.api.v1.system`):

- `SystemService.get_system_info()` for application metadata (Phase 1).
- `app.database.database.check_database_connection()` for database
  connectivity (already used by `app.lifecycle.startup.run_startup`).
- `AIRuntimeManager.health_service.runtime_status()` for runtime health
  (already used by `GET /api/v1/system/runtime`).
- `AIRuntimeManager.get_all_model_status()` for per-model status
  (already used by `GET /api/v1/system/models/status`).

Per ADR-036/ADR-047, nothing this service returns may include secrets,
credentials, environment variables, or other sensitive infrastructure
information -- it only re-packages metadata each underlying component
already considered safe to expose publicly.
"""

from typing import Any

from app.core.logging import get_logger
from app.database.database import check_database_connection
from app.ml.runtime.runtime_manager import AIRuntimeManager
from app.services.system_service import SystemService
from app.utils.environment import get_current_timestamp

logger = get_logger(__name__)


class AdminSystemService:
    """Aggregates safe, already-computed operational metadata for administrators."""

    def __init__(self, runtime_manager: AIRuntimeManager, system_service: SystemService) -> None:
        self._runtime_manager = runtime_manager
        self._system_service = system_service

    async def get_system_status(self) -> dict[str, Any]:
        """Return a combined application/database/runtime/model status snapshot."""
        application_info = self._system_service.get_application_info().model_dump()
        database_status = await self._check_database_status()
        runtime_status = await self._runtime_manager.health_service.runtime_status()
        model_statuses = await self._runtime_manager.get_all_model_status()

        logger.info(
            "Admin system status generated: database_connected=%s",
            database_status.get("connected"),
        )

        return {
            "application": application_info,
            "database": database_status,
            "runtime": runtime_status,
            "models": {"models": model_statuses},
            "generated_at": get_current_timestamp(),
        }

    @staticmethod
    async def _check_database_status() -> dict[str, Any]:
        """Return a safe database connectivity status, never leaking a driver error message."""
        try:
            await check_database_connection()
            return {"connected": True, "status": "healthy"}
        except Exception:
            logger.error("Admin system status: database connectivity check failed.", exc_info=True)
            return {"connected": False, "status": "unhealthy"}
