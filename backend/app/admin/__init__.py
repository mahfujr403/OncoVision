"""Administration & Governance domain package (Phase 7, ADR-036).

Holds cross-cutting Admin concerns -- currently just
`app.admin.exceptions` -- that don't belong inside any single existing
domain package (`app.history`, `app.reports`, ...). Admin business logic
itself lives in `app.services.admin_*`, and admin API routing lives in
`app.api.v1.admin`, matching the existing convention where domain
packages under `app/` hold framework-agnostic logic and `app/api`/
`app/services` hold the HTTP and orchestration layers.
"""
