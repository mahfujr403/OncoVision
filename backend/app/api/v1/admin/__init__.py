"""Administration API package (Phase 7, ADR-036).

Aggregates the Admin sub-routers (`users`, `history`, `system`,
`analytics`) behind a single `/admin`-prefixed `router`, mirroring how
`app.api.v1.history` aggregates its own endpoints behind
`app.api.v1.router`. Every route in this package requires administrative
authorization (`require_admin`, `app.dependencies.auth`) -- there is no
public or standard-user-facing endpoint anywhere under this package.
"""

from fastapi import APIRouter

from app.api.v1.admin import analytics, history, system, users
from app.constants.app import TAG_ADMIN

router = APIRouter(prefix="/admin", tags=[TAG_ADMIN])

router.include_router(users.router)
router.include_router(history.router)
router.include_router(system.router)
router.include_router(analytics.router)
