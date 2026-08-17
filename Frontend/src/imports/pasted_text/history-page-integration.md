# PHASE 6 — PREDICTION HISTORY

## Project Context

OncoVision AI is an enterprise-oriented AI Medical SaaS platform (lung & colon cancer histopathology classification via ensemble deep learning). The project is UNDER DEVELOPMENT — never describe it as production-ready or clinically validated.

## Current Progress (confirmed by inspecting the actual repo, not assumed)

- **Phase 4 (auth) and Phase 5 (real prediction submission/results) are both genuinely complete**, confirmed by direct source inspection, and a follow-up cleanup pass has already corrected the Phase 3-era sidebar copy (workflow steps, image requirements) and aligned the frontend's `MAX_IMAGE_SIZE_MB` with the backend's real 10 MB limit. `LoginPage`/`RegisterPage` now consistently use the `useLogin`/`useRegister` TanStack Query hooks.
- Predictions are already being persisted server-side: `save_history` defaults to `true` on every submission from `usePredictionUpload.ts`, and the backend's `PredictionService` genuinely writes to Prediction History on each request (confirmed in `prediction_service.py`) — so there is already real data accumulating for this phase to retrieve.
- `src/pages/dashboard/HistoryPage.tsx` exists but is **entirely mock**: it generates 48 fake in-memory records with `Math.random()` confidence values and fake statuses, and has no backend call anywhere.
- `src/constants/api.ts` already has `API_ENDPOINTS.PREDICTIONS.HISTORY`, `API_ENDPOINTS.PREDICTIONS.HISTORY_BY_ID(id)`, and `QUERY_KEYS.HISTORY.LIST(filters)` / `QUERY_KEYS.HISTORY.DETAIL(id)` pre-scaffolded and ready to use — do not redefine these.
- `src/hooks/usePagination.ts` (page/pageSize/goToPage/nextPage/prevPage/changePageSize/reset) and `src/hooks/useSearch.ts` already exist and are reusable, though the history list's actual filtering must ultimately be server-side per the backend contract below, not client-side array filtering as the current mock does.
- No `/dashboard/history/:historyId` (or equivalent) detail route exists yet in `src/routes/index.tsx` / `src/constants/routes.ts`.
- Reusable UI primitives already exist and were used by the mock page: `Table`/`TableHeader`/`TableBody`/`TableRow`/`TableHead`/`TableCell`, `Badge`, `Card`, `EmptyState`, `Pagination`, `SearchBox`, `SectionTitle`.

## Current Gap

`HistoryPage.tsx` shows fake data with no connection to the real, already-persisting backend history. There is no history detail view, no server-side pagination, and no server-side filtering.

## Objective

Replace the mock `HistoryPage.tsx` with a real integration against `GET /api/v1/predictions/history` (list, paginated, filterable) and `GET /api/v1/predictions/history/{history_id}` (detail), rendering only backend-provided data.

## Important Rules

- Do not rewrite the auth system (Phase 4) or the prediction submission/result flow (Phase 5) — both are complete and working, leave them alone.
- Do not invent any field, filter, or endpoint beyond what is confirmed below.
- Do not perform client-side filtering/search over a full unfiltered fetch — the backend supports real server-side filtering (`status`, `predicted_class`, `start_date`, `end_date`, `min_confidence`, `max_confidence`) and real server-side pagination; use them as query parameters on the actual request rather than fetching everything and slicing client-side, since the backend enforces per-user ownership and page bounds server-side.
- History records are immutable and read-only from the frontend's perspective — do not build any edit/delete UI for history records; none of that is supported by the backend.
- `history_id` not found and `history_id` owned by another user are both indistinguishable `404`s by design (ADR-035) — do not build UI that tries to distinguish "not found" from "not yours"; render a single generic "not found" state for both.
- Reuse the existing `Table`, `Badge`, `Card`, `EmptyState`, `Pagination`, `SearchBox` components and `usePagination`/`useSearch` hooks where they genuinely fit — extend rather than replace, but adapt their usage to drive real server-side query parameters instead of client-side array operations.
- Do not implement reports/analytics/CSV/PDF export (Phase 7), admin (Phase 8), or system/monitoring (Phase 9) in this phase.
- Do not implement admin's separate `GET /admin/history` / `GET /admin/history/{id}` in this phase — this phase is the current user's own history only (`/predictions/history*`), not the admin cross-user endpoints.

## Existing Architecture (confirmed, must be preserved/extended)

src/constants/api.ts → API_ENDPOINTS.PREDICTIONS.HISTORY, HISTORY_BY_ID(id), QUERY_KEYS.HISTORY.LIST/DETAIL already defined — use them, don't redefine
src/hooks/usePagination.ts, useSearch.ts → reusable, adapt to drive server-side params
src/pages/dashboard/HistoryPage.tsx → currently 100% mock, replace its data layer
src/components/ui/{Table,Badge,Card,EmptyState,Pagination,SearchBox,SectionTitle}.tsx → reuse
src/features/prediction/ → reference pattern from Phase 5 for service/hook/type structure (predictionService.ts, usePredictionQuery.ts, types.ts) — follow the same layering for history
src/routes/index.tsx, src/constants/routes.ts → need a new detail route added


## Backend Contract (confirmed via direct source inspection of `app/api/v1/history/{router,responses,examples}.py`, `app/history/{pagination,filters,enums}.py` — do not deviate)

Base: `/api/v1/predictions/history`. All endpoints require `Authorization: Bearer <access_token>`. Ownership is enforced server-side — a user only ever receives their own records.

**`GET /api/v1/predictions/history`**

Query parameters (all optional):
- `page`: int, ≥1, default `1`
- `page_size`: int, 1–100, default `20`
- `status`: `"pending" | "success" | "partial_success" | "failed"`
- `predicted_class`: string
- `start_date`: ISO 8601 datetime — records created on/after
- `end_date`: ISO 8601 datetime — records created on/before
- `min_confidence`: float, 0.0–100.0 (percentage, not fraction)
- `max_confidence`: float, 0.0–100.0

An inconsistent range (`start_date` after `end_date`, `min_confidence` > `max_confidence`, or `page_size`/`page` out of bounds) returns `422` with the standard `errors: [{field, message}]` shape.

Response `data` (`PredictionHistoryListResponseSchema`):
```json
{
  "items": [
    {
      "history_id": "string",
      "request_id": "string",
      "status": "pending" | "success" | "partial_success" | "failed",
      "created_at": "ISO-8601",
      "image_filename": "string",
      "predicted_class": "string | null",
      "confidence": 0.0,
      "agreement_ratio": 0.0,
      "successful_models": ["string"],
      "failed_models": ["string"],
      "participating_models": 0,
      "individual_predictions": [
        { "model_name": "string", "prediction": "string", "confidence": 0.0, "inference_time_ms": 0.0 }
      ]
    }
  ],
  "count": 0,
  "pagination": {
    "current_page": 0,
    "page_size": 0,
    "total_records": 0,
    "total_pages": 0,
    "has_next": false,
    "has_previous": false
  }
}
```

**`GET /api/v1/predictions/history/{history_id}`**

Response `data` (`PredictionHistoryDetailResponseSchema`) — same core fields as a list item, plus:
```json
{
  ...same fields as list item except no "pagination" wrapper...,
  "image_metadata": {
    "filename": "string",
    "content_type": "string",
    "size_bytes": 0,
    "width": 0,
    "height": 0
  },
  "runtime_info": {
    "model_manifest_version": "string | null",
    "processing_time_ms": 0.0 | null
  }
}
```

`confidence` and per-model `confidence` are already percentages (0–100), same convention as Phase 5 — render directly.

Confirmed error responses:
- `401` — missing/invalid auth
- `404` — (detail endpoint only) record not found or not owned by current user — single indistinguishable generic case
- `422` — (list endpoint only) invalid/inconsistent query parameters
- `500` — unexpected internal error

## Required Implementation

1. **Types** — Add `PredictionHistoryItem`, `PredictionHistoryListResponse`, `PredictionHistoryPagination`, `PredictionHistoryDetail`, `PredictionHistoryFilters` (matching the query params above) to `src/types/` or `src/features/history/types.ts`, matching the schemas exactly.
2. **History service** — Add a `historyService` (e.g. `src/features/history/services/historyService.ts`, mirroring `predictionService.ts`'s structure) with `listHistory(params)` and `getHistoryDetail(id)`, using `API_ENDPOINTS.PREDICTIONS.HISTORY` / `HISTORY_BY_ID(id)` already defined in `constants/api.ts`.
3. **TanStack Query hooks** — Add `useHistoryList(filters)` (a `useQuery` keyed by `QUERY_KEYS.HISTORY.LIST(filters)`, refetching when filters/page change) and `useHistoryDetail(id)` (keyed by `QUERY_KEYS.HISTORY.DETAIL(id)`), following the pattern already established in `useAuthQueries.ts` and `usePredictionQuery.ts`.
4. **List page rewrite** — Replace `HistoryPage.tsx`'s mock data generation with `useHistoryList`, driving `page`/`page_size` from `usePagination` and search/filter inputs into the real query parameters (server-side), not client-side array filtering.
5. **Filter UI** — Add filter controls for at least `status` and a confidence range, and optionally a date range and `predicted_class`, wired to the real query parameters. The existing `Filter` button in the current mock page is currently non-functional — wire it to a real filter panel/dropdown.
6. **Detail view** — Add a new detail route (inspect `src/constants/routes.ts` for the naming convention already used, e.g. alongside `HISTORY: '/dashboard/history'`, add something like `HISTORY_DETAIL: (id: string) => \`/dashboard/history/${id}\`` following whatever pattern `ADMIN.USER_BY_ID`-equivalent patterns elsewhere in the app use) and a corresponding page component rendering `useHistoryDetail(id)`'s full result — reuse the Phase 5 result-rendering components (`PredictionResultCard`, `IndividualModelsCard`) where their shape genuinely matches, adapting for the additional `image_metadata`/`runtime_info` fields unique to the detail response.
7. **Row navigation** — Make each history table row navigate to its detail route.
8. **Loading/empty/error states** — Real loading skeletons during fetch, a real empty state when `items` is empty (distinct copy for "no predictions yet" vs "no results match your filters"), and a real error state for 401/422/500.

## Files / Architecture

src/types/ (or src/features/history/types.ts) — new history types
src/features/history/services/historyService.ts (new)
src/features/history/hooks/ (new: useHistoryList, useHistoryDetail)
src/features/history/components/ (new: filter panel, detail-specific components as needed)
src/pages/dashboard/HistoryPage.tsx (rewrite data layer, keep/reuse existing table markup where it fits)
src/pages/dashboard/ (new: HistoryDetailPage.tsx or similar)
src/constants/routes.ts, src/routes/index.tsx (add detail route)

Do not modify `src/api/axios-instance.ts`, `src/api/interceptors.ts`, anything under `src/features/auth/`, or `src/features/prediction/`'s submission flow.

## API Integration

- `GET /api/v1/predictions/history?page=&page_size=&status=&predicted_class=&start_date=&end_date=&min_confidence=&max_confidence=` — only include parameters that are actually set; don't send empty-string filter params.
- `GET /api/v1/predictions/history/{history_id}` — path param, no query params.
- Both use the shared `axiosInstance` (Bearer token already attached automatically).
- On filter/page change, the query should refetch — use TanStack Query's `queryKey` dependency on the filter/page object rather than manual refetch calls.

## State Management

- **TanStack Query**: history list (paginated/filtered) and history detail, both as `useQuery`.
- **Local/URL state**: current page, page size, and active filters — consider reflecting filters in the URL (query string) so a detail-page-back-navigation returns to the same filtered/paginated list, but this is a nice-to-have, not a hard requirement; if not done, state clearly in your report that filters reset when navigating away and back.
- Do not duplicate the list data into a separate global store — TanStack Query's cache is sufficient.

## UI/UX

- Reuse `Table`/`TableRow`/`TableCell` for the list, `Pagination` for page controls, `SearchBox`/new filter controls for filtering, `EmptyState` for empty results, `Badge` for status (reuse the same status→badge-variant mapping convention established in `PredictionResultCard.tsx` from Phase 5: success=success badge, partial_success=warning badge, failed=destructive badge, pending=default).
- Detail page should visually echo the Phase 5 result view for consistency, since it's showing the same underlying data shape retrospectively.
- Medical disclaimer language conventions continue to apply on the detail view exactly as in Phase 5.
- Loading: skeleton rows/cards, not a blank screen.
- Responsive: table should degrade sensibly on mobile (stack or horizontal scroll, matching whatever pattern the existing `Table` component already supports).

## Security

- Never attempt to fetch or display another user's history — there is no client-side capability to do so anyway since the backend enforces ownership, but do not build any UI that implies a `user_id` or similar parameter could be supplied to broaden results.
- Do not log full history payloads to the console in production code paths.

## Performance

- Set reasonable `staleTime`/`gcTime` on the list query — history changes when new predictions are submitted, so don't cache so aggressively that a user who just ran a new prediction doesn't see it; consider invalidating `QUERY_KEYS.HISTORY.LIST` on successful prediction submission (Phase 5's `useCreatePrediction` `onSuccess`) if that's a small, safe addition — flag it as an option rather than assuming it's required scope.
- Debounce any text-based filter input (e.g. `predicted_class` free-text) before it drives a new query.

## Testing

- List loads real data, paginates correctly using backend-provided `pagination` metadata (not recomputed client-side).
- Each filter (status, confidence range, date range, predicted_class) independently narrows results correctly against the real backend.
- Invalid filter combination (e.g. start_date after end_date) surfaces the backend's real 422 message.
- Empty state: no predictions yet (new user) vs. no results for current filters — distinct copy.
- Detail view loads a real record correctly.
- 404 on detail (deleted/foreign/nonexistent id) shows a single generic not-found state.
- 401 on either endpoint correctly triggers the existing Phase 4 auth/refresh flow, not a broken page.
- Regression: Phase 5 prediction submission/result flow and Phase 4 auth are unaffected.
- Responsive and accessibility checks on both list and detail views.

## Edge Cases

- Page number requested beyond `total_pages` (e.g. stale pagination state after a filter narrows results) — should not crash; reset to page 1 or show a clear "no results" state.
- A prediction still `pending`/mid-pipeline appearing in history (if that's even persisted — verify against actual backend behavior rather than assuming) — render gracefully if `predicted_class`/`confidence` fields are in their default/null-ish state.
- Very long `image_filename` values — ensure table truncation matches the pattern already used in the mock page.

## Definition of Done

- [ ] `HistoryPage.tsx` shows only real backend data — no `Math.random()`, no mock array, no client-side pagination math.
- [ ] Server-side pagination and all six filter parameters work against the real backend.
- [ ] A working history detail page/route exists, rendering the full `PredictionHistoryDetailResponseSchema` shape including `image_metadata` and `runtime_info`.
- [ ] 404/422/401/500 are all handled with real, backend-sourced messaging.
- [ ] No invented fields, endpoints, or client-side recalculation of any confidence/agreement/status value.
- [ ] Existing Phase 4/5 functionality is unaffected (regression-checked).
- [ ] Loading/empty/error states implemented, accessible, and responsive for both list and detail.

## Explicitly Do NOT Implement

- Reports/analytics/CSV/PDF export (Phase 7).
- Admin history endpoints (`/admin/history*`) — different endpoints, different phase (Phase 8).
- Any edit/delete/favorite/annotate capability on history records — not supported by the backend.
- System/monitoring screens (Phase 9).

## Final Instruction

Before writing any code, inspect `src/constants/routes.ts` and `src/routes/index.tsx` to determine the cleanest way to add a detail route consistent with existing naming, and confirm the `Table`/`Pagination`/`EmptyState` component APIs by reading their actual current props rather than assuming. Modify only what is necessary to complete this phase. Do not rewrite Phase 4 or Phase 5 working code. Do not invent APIs or fields. Do not use fake data. After implementation, report exactly which files were changed, any assumptions made, and stop — do not proceed to Phase 7 automatically.