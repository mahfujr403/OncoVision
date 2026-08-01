"""Central API router aggregating all versioned sub-routers.

Adding a new API version (e.g. `v2`) only requires creating the new
sub-package and including its router here.
"""

from fastapi import APIRouter

from app.api.v1 import auth, health, predictions, system

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(system.router)
api_router.include_router(auth.router)
api_router.include_router(predictions.router)
