# PHASE 7 — REPORTS & ANALYTICS (Figma-First)

## Project Context
OncoVision AI is an enterprise-oriented AI Medical SaaS platform for AI-assisted Lung & Colon Cancer Histopathology classification via ensemble deep learning. The project is UNDER DEVELOPMENT — never describe it as production-ready, clinically validated, or medically approved. Language must stay in the register of "AI Prediction," "Predicted Class," "Model Confidence," "AI-assisted Analysis" — never "diagnosis confirmed" or similar.

## Current Project State (confirmed by direct repo inspection)
- **Phase 4 (Auth)** and **Phase 5 (Prediction)** are genuinely complete and must not be touched.
- **Phase 6 (Prediction History)** is genuinely complete: `src/features/history/` (`historyService.ts`, `useHistoryQueries.ts`, list + detail pages) is real, server-side paginated and filtered against `GET /api/v1/predictions/history` and `GET /api/v1/predictions/history/{history_id}`. Do not touch it.
- `src/pages/dashboard/ReportsPage.tsx` currently renders a hardcoded `MOCK_REPORTS` array with zero backend calls. This is the only remaining artifact of this phase and must be replaced.
- `src/constants/api.ts` already defines `API_ENDPOINTS.REPORTS.{ANALYTICS, EXPORT_CSV, EXPORT_PDF}` and `QUERY_KEYS.REPORTS.ANALYTICS` — reuse these verbatim, do not redefine.
- `src/constants/routes.ts` already has `ROUTES.REPORTS = '/dashboard/reports'` — reuse, do not add new routes unless a genuine sub-view is needed (state that assumption if you add one).
- No `src/features/reports/` directory exists yet — this phase creates it, mirroring the exact layering already used in `src/features/history/` (`services/`, `hooks/`, `types.ts`).

## Phase 6 Completion Summary
Real history list + detail integration is done and stable. Reports & Analytics is the next undone item in the documented roadmap (Phase 7) and is the only remaining mock page with a real, documented backend contract. Other mock pages in the repo (Comparison, Benchmark, Favorites, Saved Cases, Notifications) have **no corresponding backend endpoint anywhere in the API surface** and are explicitly out of scope — do not touch or "complete" them in this phase.

## Recommended Next Phase
**Phase 7 — Reports & Analytics**, covering the Analytics Dashboard view and CSV/PDF export, replacing the mock `ReportsPage.tsx` with real backend integration.

## Objective
Replace the mock Reports page with a real analytics dashboard driven by `GET /api/v1/reports/analytics`, plus real CSV/PDF export actions driven by `GET /api/v1/reports/export/csv` and `GET /api/v1/reports/export/pdf`. Render only backend-provided metrics.

## Why This Phase Comes Next
It is the next phase in the documented roadmap, it has a real scaffolded API contract already partially wired into `constants/api.ts`, and it depends on nothing except Auth (already complete) — unlike Admin (Phase 8) or System/Monitoring (Phase 9), which depend on different, not-yet-consumed endpoints, and unlike Comparison/Favorites/Notifications, which have no backend support at all.

## Important Rules
- Do not rewrite or modify Auth (Phase 4), Prediction (Phase 5), or History (Phase 6) — all three are complete and working.
- Do not invent any analytics metric (accuracy, precision, recall, F1, ROC, etc.) that is not literally returned by `GET /api/v1/reports/analytics`. Before implementing, inspect the actual backend router/Pydantic response schema for this endpoint (e.g. `app/api/v1/reports/{router,responses}.py` or equivalent) to confirm the exact field names and shapes. Do not assume the shape from this prompt — this prompt describes the UI requirement, the backend source is authoritative for the contract.
- Do not invent a "generate report" or "saved reports list" feature — the backend only exposes analytics + two export endpoints, not a report-generation/storage system. The current mock's "Generate report" button and `MOCK_REPORTS` list of named report artifacts must be removed entirely; there is no backend support for stored/named reports.
- CSV/PDF export must trigger the real `GET /reports/export/csv` / `GET /reports/export/pdf` endpoints (as file downloads via Axios with `responseType: 'blob'`, triggering a browser download), not a client-side generated file.
- Do not implement Admin (Phase 8) or System/Monitoring (Phase 9) in this phase.
- Do not implement Comparison, Benchmark, Favorites, Saved Cases, or Notifications — leave those pages as-is; they are tracked separately and have no backend contract yet.
- Reuse `API_ENDPOINTS.REPORTS` and `QUERY_KEYS.REPORTS.ANALYTICS` from `src/constants/api.ts` exactly as already defined.

## Existing Architecture (must be preserved/extended, not replaced)

src/constants/api.ts → API_ENDPOINTS.REPORTS.{ANALYTICS,EXPORT_CSV,EXPORT_PDF}, QUERY_KEYS.REPORTS.ANALYTICS already defined — use them
src/pages/dashboard/ReportsPage.tsx → currently 100% mock, replace its data layer and remove the "generate/named reports" concept entirely
src/features/history/ → reference pattern for services/hooks/types layering (historyService.ts, useHistoryQueries.ts, types.ts) — mirror this exactly for src/features/reports/
src/components/ui/{Card,CardHeader,CardTitle,CardDescription,CardContent,MetricCard,StatCard,Badge,EmptyState,SectionTitle,Skeleton,ErrorState}.tsx → reuse
src/api/axios-instance.ts → reuse for the blob-download export requests
src/routes/index.tsx, src/constants/routes.ts → ROUTES.REPORTS already exists, no new route needed unless a genuinely separate export/history-of-exports view is required (do not invent one)


## Backend Contract
Base: `/api/v1/reports`. All endpoints require `Authorization: Bearer <access_token>`.
- `GET /api/v1/reports/analytics` — returns aggregate prediction analytics for the current user (or admin-scoped, if applicable — confirm from source). **Do not assume specific fields (e.g. class distribution, confidence distribution, totals over time) — inspect the actual Pydantic response schema before building the UI's data bindings.**
- `GET /api/v1/reports/export/csv` — returns a CSV file stream/attachment.
- `GET /api/v1/reports/export/pdf` — returns a PDF file stream/attachment.

Before writing any UI component that binds to a specific analytics field, the coding AI must first open and read the actual backend router + response schema for `/reports/analytics` in the backend repo and confirm the literal field names. If the backend repo is not available in this environment, the coding AI must say so explicitly and implement the data layer (types/service/hook) generically against whatever the actual JSON response contains, rather than guessing field names, and flag any assumption made.

## Figma Design Requirements
Design first in Figma before implementation, using the OncoVision design language already established (do not introduce a new visual language).

## Design System (reuse, do not replace)
- Colors: CSS variables in `src/index.css` — `--primary` (OKLCH blue, `oklch(0.62 0.18 220)` dark / `oklch(0.48 0.18 220)` light), `--accent` (teal, `oklch(0.58 0.20 195)`), `--muted`, `--border`, `--destructive`, full dark/light pair already defined via `.dark`/root selectors.
- Typography: `Inter` (body, `--font-sans`), `Sora` (display/headings, `--font-display`), `JetBrains Mono` (numeric/technical, `--font-mono`).
- Radius: `--radius: 0.5rem` with `--radius-sm/md/lg` derived tokens.
- Components: `Card`/`CardHeader`/`CardTitle`/`CardDescription`/`CardContent`, `MetricCard`, `StatCard`, `Badge` (variant + `dot` prop), `Table`/`TableHeader`/`TableBody`/`TableRow`/`TableHead`/`TableCell`, `EmptyState`, `Skeleton`, `ErrorState`, `SectionTitle` (title/description/action slot), `Button`.

## Pages to Design

### Reports & Analytics Dashboard
#### Purpose
Give the user (and later admin, if the endpoint is user-scoped vs. global — confirm from source) a read-only view of their aggregate prediction analytics, with export actions.
#### User Goal
Understand prediction volume, class distribution, and confidence trends at a glance; export the underlying data as CSV or PDF.
#### Layout
`SectionTitle` header ("Reports & Analytics" / short description) with export actions (CSV, PDF buttons) in the action slot — replacing the current "Generate report" button. Below: a grid of `MetricCard`/`StatCard` summary tiles (exact metrics driven by the real response, e.g. total predictions, most common predicted class — only what the API actually returns), followed by one or two chart/visualization blocks (e.g. class distribution, confidence distribution) if the backend response supports them structurally, using a lightweight charting approach consistent with the existing stack (no new charting library without justification — check if one is already a dependency before adding).
#### Components
`SectionTitle`, `MetricCard`/`StatCard` grid, `Card` containers for chart blocks, `Badge` for export format indicators, `Button` (CSV export, PDF export) with loading state during download.
#### Data
Exclusively from `GET /reports/analytics` for the on-screen metrics; `GET /reports/export/csv` and `GET /reports/export/pdf` only triggered on button click, not rendered inline.
#### Interactions
CSV/PDF buttons: default → loading spinner during download → success toast (via `Sonner`, already in stack) → back to default. Failure → error toast, button re-enabled.
#### States
Initial loading (skeleton grid matching the metric-card layout), loaded, empty (zero predictions yet — distinct copy from a fetch error), error (401/500), export-in-progress (per-button), export-failed (toast, non-blocking).
#### Desktop (1440px+)
Full metric grid (3–4 columns), charts side-by-side where two exist.
#### Tablet (768–1439px)
Metric grid collapses to 2 columns, charts stack vertically.
#### Mobile (320–767px)
Metric grid single column, charts full-width and stack, export buttons stack or move into a single dropdown/menu if space is constrained.
#### Accessibility
Chart data must have an accessible text/table fallback or `aria-label` summary; export buttons need clear `aria-busy` state during download; all metric tiles readable by screen reader in a sensible order.

## Reusable Components
Reuse `Card`, `CardHeader`, `CardTitle`, `CardDescription`, `CardContent`, `MetricCard`, `StatCard`, `Badge`, `EmptyState`, `Skeleton`, `ErrorState`, `SectionTitle`, `Button` exactly as they exist. Do not create parallel versions.

## API Integration

GET /reports/analytics → reportsService.getAnalytics() → useReportsAnalytics() (TanStack Query, key: QUERY_KEYS.REPORTS.ANALYTICS)
GET /reports/export/csv → reportsService.exportCsv() → triggered imperatively on click, Axios responseType: 'blob', not a query hook
GET /reports/export/pdf → reportsService.exportPdf() → same pattern as CSV


## TypeScript Types
Add to `src/features/reports/types.ts`, matching the real backend response exactly (confirm field names from source before typing — do not guess).

## TanStack Query
`useReportsAnalytics()` in `src/features/reports/hooks/useReportsQueries.ts`, following the exact pattern of `useHistoryQueries.ts`.

## Routing
No new route required — `ROUTES.REPORTS` already exists and already points at this page.

## Loading States
Skeleton metric-card grid while `useReportsAnalytics` is loading; per-button spinner state for CSV/PDF export in progress.

## Empty States
Distinct "No predictions yet — analytics will appear once you run your first prediction" copy when the backend returns zero underlying data, separate from any error state.

## Error States
Real error UI (`ErrorState` component) for 401 (redirect/session handling already exists at the Axios interceptor layer — do not duplicate it) and 500 (retry action).

## Responsive Behavior
As specified per breakpoint above; sidebar/nav behavior is already handled globally by `DashboardLayout`/`Sidebar` — do not modify those.

## Accessibility
Keyboard-reachable export buttons, visible focus states (already defined globally via `--ring`), sufficient color contrast for chart elements against both dark and light themes, reduced-motion respect for any chart entrance animation.

## Performance
Avoid re-fetching analytics on every render; rely on TanStack Query's caching. Do not re-fetch on export click.

## Security
Do not expose any raw backend error internals in the UI; rely on the existing normalized Axios error handling.

## Testing
- Happy path: analytics load and render real metrics.
- Empty state: zero-prediction user sees empty copy, not a broken chart.
- 401: handled by existing global interceptor, verify no duplicate handling added here.
- 500: `ErrorState` renders with retry.
- CSV export: triggers real download, button shows loading → success.
- PDF export: same.
- Export failure: toast shown, button recovers.
- Responsive check at 1440px, 768px, 375px.
- Accessibility: keyboard-only pass through export buttons and metric grid.

## Edge Cases
- Backend returns partial/null fields for some metrics — render gracefully (e.g. "—" or omit the tile), never fabricate a fallback numeric value.
- Export request fails after a long-running generation — must not hang the button indefinitely; use a reasonable timeout consistent with the existing Axios instance config.

## Definition of Done
- Mock `MOCK_REPORTS` array and "Generate report" concept fully removed.
- `src/features/reports/` created mirroring `src/features/history/` layering (types, services, hooks).
- Real `GET /reports/analytics` integration renders only backend-provided fields, confirmed against actual backend schema (not assumed from this prompt).
- Real CSV and PDF export via `GET /reports/export/csv` and `GET /reports/export/pdf`, triggering actual file downloads.
- Loading, empty, and error states all real and distinct.
- No existing architecture (Auth, Prediction, History) modified.
- No unrelated pages (Admin, Comparison, Benchmark, Favorites, Saved Cases, Notifications) touched.
- Responsive and accessible per the above.
- No invented metrics, endpoints, or fields anywhere in the implementation.

## Explicitly Do NOT Implement
- Admin (Phase 8) in any form.
- System/Monitoring (Phase 9).
- Comparison, Benchmark, Favorites, Saved Cases, Notifications pages (no backend contract exists for these).
- A "named/stored reports" list or "generate report" workflow — not supported by the backend contract.
- Any change to Auth, Prediction, or History features.

## Final Implementation Instructions
Design the Reports & Analytics dashboard in Figma first, following the design system tokens and components above, across desktop/tablet/mobile. Before implementing, inspect the actual backend `/reports/analytics`, `/reports/export/csv`, `/reports/export/pdf` router and Pydantic schemas in the backend source to confirm the exact response shape — do not implement against assumed field names. Then implement into the existing React codebase, extending `src/features/reports/` and replacing `ReportsPage.tsx`'s data layer, preserving all existing architecture. Stop after this phase — do not proceed to Admin or System/Monitoring without further instruction.