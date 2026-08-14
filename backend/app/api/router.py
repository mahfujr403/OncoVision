"""Central API router aggregating all versioned sub-routers.

Adding a new API version (e.g. `v2`) only requires creating the new
sub-package and including its router here.
"""

from fastapi import APIRouter

from app.api.v1 import auth, health, history, monitoring, predictions, reports, system
from app.api.v1.admin import router as admin_router

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(system.router)
api_router.include_router(auth.router)
api_router.include_router(predictions.router)
api_router.include_router(history.router)
api_router.include_router(reports.router)
api_router.include_router(admin_router)
api_router.include_router(monitoring.router)
