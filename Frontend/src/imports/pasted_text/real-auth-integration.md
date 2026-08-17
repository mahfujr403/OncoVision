# PHASE 4 — REAL BACKEND INTEGRATION & AUTHENTICATION

## Project Context

OncoVision AI is an enterprise-oriented AI Medical SaaS platform (lung & colon cancer histopathology classification via ensemble deep learning). The project is UNDER DEVELOPMENT — never describe it as production-ready or clinically validated.

Backend: FastAPI + PostgreSQL, real JWT auth, already implemented and confirmed via source inspection.
Frontend: React 19 + TypeScript + Vite + Tailwind + shadcn/ui + TanStack Query + Axios + React Hook Form + Zod, feature-based architecture.

## Current Progress (confirmed by inspecting the actual repo, not assumed)

- Phase 1 (Foundation), Phase 2 (Auth UI foundation), Phase 3 (Prediction upload UX) are complete.
- `src/api/axios-instance.ts`, `src/api/interceptors.ts`, `src/api/index.ts` exist with a working request interceptor (Bearer token attach) and response interceptor skeleton, but the 401/refresh branch is an explicit placeholder that just clears tokens and redirects — it does not call any refresh endpoint.
- `src/contexts/AuthContext.tsx` provides `user`, `token`, `role`, `isAuthenticated`, `isLoading`, `login`, `logout`, `refreshSession`, `updateUser` — the shape is reusable, but internally it calls the mock `authService` and reads/writes `localStorage`/`sessionStorage` session objects.
- `src/features/auth/services/authService.ts` is a fully mocked, localStorage-backed fake backend: fake token generation via `btoa()`, a fake user store, and seeded demo accounts using **roles that do not exist on the backend** (`researcher`, `doctor`) plus fields the backend does not return (`institution`, `specialty`).
- `src/types/index.ts` defines `UserRole = 'admin' | 'doctor' | 'researcher' | 'viewer'` and a `User` interface with fields that do not match the backend `UserResponse` schema, and an `ApiResponse<T>` type that does not match the backend's actual envelope.
- `src/routes/guards.tsx` has `ProtectedRoute`, `PublicRoute`, `AdminRoute` (reusable), plus `ResearcherRoute`, `RoleRoute`, `PermissionRoute` which depend on the invented roles/permission system in `src/utils/permissions.ts`.
- No auth page (`LoginPage`, `RegisterPage`, `ForgotPasswordPage`, `ResetPasswordPage`, `VerifyEmailPage`) uses TanStack Query — they call the mock service directly.
- `src/providers/index.tsx` already wires `QueryClientProvider`, `ThemeProvider`, `AuthProvider`, and `Toaster` correctly and needs no structural change.

## Current Gap

There is no real connection to the FastAPI backend. Authentication is entirely simulated client-side. There is no real token refresh flow, no request queueing during refresh, and the type system encodes a role/permission model the backend does not support.

## Objective

Replace the mocked authentication system with real integration against the FastAPI backend's confirmed `/api/v1/auth/*` endpoints, while preserving the existing component structure, context shape, provider setup, and route guard pattern wherever they don't depend on invented data.

## Important Rules

- Do not rewrite `src/providers/index.tsx`, `src/api/axios-instance.ts`, or the overall feature-based folder structure — extend them.
- Do not invent any backend endpoint, field, or role beyond what is confirmed below.
- Remove the `researcher`, `doctor`, `viewer` roles and all role-specific UI/route logic built on them (`ResearcherRoute`, and any permission logic keyed to those roles) — the backend only supports `admin` and `user`. If any UI currently branches on those roles, it must be updated to reflect only `admin`/`user`, or removed if it has no backend-supported equivalent.
- Delete/retire the mock `authService.ts` localStorage simulation (token generation, fake user store, seeded demo accounts) once real integration is complete. Do not leave dead mock code wired into the active auth flow.
- Reuse `AuthContext`'s existing state shape (`user`, `isAuthenticated`, `isLoading`, `login`, `logout`) as the target public API where possible so downstream consumers (guards, nav, profile) need minimal changes — but its internals must call real services.
- Reuse `src/api/axios-instance.ts` and the interceptor pattern in `src/api/interceptors.ts` — implement the real refresh logic inside the existing 401 handler rather than replacing the file.
- Do not implement prediction submission, prediction results rendering, or any `/predictions` integration in this phase — Phase 3's upload UI stays UI-only until Phase 5.
- Do not implement history, reports, admin data screens, or monitoring in this phase.
- Before writing code, inspect `app/services/auth_service.py`, `app/dependencies/auth.py`, and `app/core/security.py` (or equivalent) in the backend to confirm exact error status codes (401 vs 400 vs 422) and error payload `errors` shape for invalid credentials, expired/revoked refresh tokens, and inactive accounts, since this was not exhaustively inspected and must not be assumed.

## Existing Architecture (confirmed, must be preserved)

src/api/axios-instance.ts → single Axios instance, baseURL from VITE_API_BASE_URL via constants/api.ts
src/api/interceptors.ts → request interceptor attaches Bearer token; response interceptor has 401 placeholder
src/api/index.ts → wires interceptors onto the instance, re-exports token helpers
src/contexts/AuthContext.tsx→ React context: user/token/role/isAuthenticated/isLoading + login/logout/refreshSession/updateUser
src/hooks/useAuth.ts → context consumer hook
src/routes/guards.tsx → ProtectedRoute, PublicRoute, AdminRoute (reusable) + role-based guards (need cleanup)
src/features/auth/ → services/, components/ (AuthErrorAlert, PasswordStrength, AuthDivider, DemoCredentials), hooks/
src/pages/auth/ → LoginPage, RegisterPage, ForgotPasswordPage, ResetPasswordPage, VerifyEmailPage
src/providers/index.tsx → QueryClientProvider + ThemeProvider + AuthProvider + Toaster (no change needed)


## Backend Contract (confirmed via source inspection — do not deviate)

Base URL: `VITE_API_BASE_URL=http://localhost:8000/api/v1`

Response envelope (all endpoints):
```json
{
  "success": true,
  "message": "string",
  "data": {},
  "errors": null,
  "request_id": "uuid",
  "timestamp": "ISO-8601"
}
```

**`POST /api/v1/auth/register`** — 201 on success
Request:
```json
{
  "full_name": "string (2-255 chars)",
  "email": "string (email)",
  "password": "string (8-128, requires upper, lower, digit, special char)",
  "confirm_password": "string (must match password)"
}
```
Response `data`: `{ "user": UserResponse }`

**`POST /api/v1/auth/login`**
Request: `{ "email": "string", "password": "string" }`
Response `data`: `{ "user": UserResponse, "access_token": "string", "refresh_token": "string", "token_type": "Bearer", "expires_in": <int seconds> }`
Optional headers the backend reads (not required): `X-Device-Name`.

**`POST /api/v1/auth/refresh`**
Request: `{ "refresh_token": "string" }`
Response `data`: `{ "access_token": "string", "refresh_token": "string", "token_type": "Bearer", "expires_in": <int> }`

**`POST /api/v1/auth/logout`**
Request: `{ "refresh_token": "string" }`
Response: message only, `data: null`.

**`POST /api/v1/auth/logout-all`**
Requires `Authorization: Bearer <access_token>`. No request body. `data: null`.

**`GET /api/v1/auth/me`**
Requires `Authorization: Bearer <access_token>`.
Response `data`: `{ "user": UserResponse }`

`UserResponse`:
```json
{
  "id": "uuid",
  "full_name": "string",
  "email": "string",
  "role": "admin" | "user",
  "is_active": true,
  "is_verified": true,
  "avatar_url": "string | null",
  "last_login": "ISO-8601 | null",
  "created_at": "ISO-8601"
}
```

Roles: strictly `"admin" | "user"`. Registration always creates `"user"` role — there is no client-selectable role at registration.

Error status codes and exact `errors` payload shape for invalid login, expired/revoked refresh token, and duplicate email were NOT exhaustively confirmed in this inspection pass — inspect `app/services/auth_service.py` and `app/dependencies/auth.py` before implementing error-state UI copy, and use whatever the backend actually returns rather than guessing.

## Required Implementation

1. **API types** — Replace `User`, `UserRole`, `AuthTokens`, `ApiResponse<T>`, `ApiError` in `src/types/` (or a new `src/types/api.ts` / `src/types/auth.ts` if that better matches the existing convention) so they exactly match the backend envelope and `UserResponse`/`LoginResponse`/`RefreshResponse` schemas above. Remove `doctor`, `researcher`, `viewer` from `UserRole` and any `User` fields not present in `UserResponse` (`institution`, `specialty`, etc.) unless they are still needed purely for local UI state — if so, mark them clearly as frontend-only and not backend-sourced.
2. **Auth service** — Rewrite `src/features/auth/services/authService.ts` to call the real endpoints via the shared Axios instance (register, login, refresh, logout, logoutAll, getMe). Remove the localStorage mock user store, fake token generation, and seeded demo accounts.
3. **Token storage** — Reuse the existing `getAccessToken`/`setTokens`/`clearTokens` helpers in `src/api/interceptors.ts`; ensure the refresh token is also persisted there (or in a clearly-named sibling helper) rather than duplicating storage logic in `authService`.
4. **Token refresh interceptor** — Implement the real refresh flow inside `src/api/interceptors.ts`'s existing 401 handler: on 401, call `POST /auth/refresh` with the stored refresh token, update stored tokens on success, retry the original request; on refresh failure, clear tokens and redirect to `/login`. Prevent infinite loops (respect `_retry`) and prevent duplicate concurrent refresh calls by queueing pending requests while a refresh is in flight.
5. **TanStack Query hooks** — Add auth query/mutation hooks (e.g. `useLogin`, `useRegister`, `useLogout`, `useLogoutAll`, `useCurrentUser`) in `src/features/auth/` following the existing feature-based convention. `useCurrentUser` should back `GET /auth/me` for session validation/restoration.
6. **AuthContext integration** — Update `AuthContext.tsx` to source its state from real login/me responses instead of the mock session object, while keeping its existing public shape (`user`, `isAuthenticated`, `isLoading`, `login`, `logout`) so guards and consumers need minimal changes. Session restoration on app load should call `GET /auth/me` (using a persisted access token) rather than reading a mock localStorage session blob.
7. **Route guards cleanup** — Update `src/routes/guards.tsx` and `src/utils/permissions.ts` to only reason about `admin`/`user`. Remove `ResearcherRoute` and any permission branches with no backend-supported role, or repoint them to `admin`/`user` only if the UI still needs that route shape.
8. **Auth pages** — Update `LoginPage`, `RegisterPage`, `ForgotPasswordPage`, `ResetPasswordPage`, `VerifyEmailPage` to use the new mutation hooks instead of calling `authService` directly. Note: the backend contract confirmed above has no `forgot-password`, `reset-password`, or `verify-email` endpoints — before touching those three pages, inspect the backend for any such endpoints; if none exist, those pages must be left as clearly non-functional/"not yet available" states rather than wired to fake success, and must not claim to send real emails.
9. **Register form fields** — Update the register form/schema to match the real payload: `full_name`, `email`, `password`, `confirm_password` (no role selector, since role is server-assigned).

## Files / Architecture

Primary areas to modify (inspect current content before editing, do not assume paths beyond what's listed):

src/types/index.ts (or split into src/types/auth.ts, src/types/api.ts)
src/api/interceptors.ts
src/features/auth/services/authService.ts
src/features/auth/ (new: hooks/ or queries/ for TanStack Query hooks)
src/contexts/AuthContext.tsx
src/routes/guards.tsx
src/utils/permissions.ts
src/pages/auth/LoginPage.tsx
src/pages/auth/RegisterPage.tsx
src/pages/auth/ForgotPasswordPage.tsx
src/pages/auth/ResetPasswordPage.tsx
src/pages/auth/VerifyEmailPage.tsx

Do not modify `src/providers/index.tsx`, `src/api/axios-instance.ts` (base config), or the folder structure itself.

## API Integration

- All auth calls go through the existing shared `axiosInstance` (`src/api/index.ts`) — do not create a second Axios instance.
- Request/response bodies must match the schemas in "Backend Contract" exactly.
- `logout` and `logout-all` require the current refresh token / access token respectively per the contract above.
- On any mutation error, surface the backend's actual `message` (and `errors` detail map when present) rather than a generic string — but do not invent error copy for cases not confirmed by inspecting the backend service layer.
- Invalidate/reset the `currentUser` query on login, logout, and logout-all.

## State Management

- **TanStack Query**: `currentUser` (from `/auth/me`), login/register/logout/logout-all as mutations.
- **Context**: authentication session state (`user`, `isAuthenticated`, `isLoading`) — sourced from the query/mutation results, not duplicated business logic.
- **Local component state**: form input state, password visibility toggle, form validation state (already handled by React Hook Form + Zod).
- **Zod schemas**: update to match the real register/login payload constraints (password complexity rules from `RegisterRequest.validate_password_strength` — upper, lower, digit, special char, min 8 chars).

## UI/UX

- Preserve existing page layouts, `AuthErrorAlert`, `PasswordStrength`, `AuthDivider` components — reuse them, don't rebuild.
- Remove or clearly repurpose `DemoCredentials` component since it references the mock seeded accounts (`admin@oncovision.ai` etc.) that will no longer exist.
- Loading states: disable submit buttons and show a loading indicator during login/register/refresh mutations.
- Error states: render backend error messages via the existing `AuthErrorAlert` component.
- Success states: existing toast (`Sonner`, already wired in `providers/index.tsx`) for register/login/logout success.

## Security

- Never log tokens or passwords to the console.
- Never expose the refresh token outside of the token storage helpers.
- Ensure the Authorization header is only attached to same-origin/API requests, not third-party calls.
- Clear all tokens and query cache on logout and logout-all.

## Performance

- Deduplicate concurrent 401-triggered refresh calls (single in-flight refresh, queued retries).
- Use TanStack Query's cache appropriately for `currentUser` (short/no stale time is fine given auth sensitivity — use your judgment but avoid refetching on every render).

## Testing

- Register: valid payload succeeds; weak password rejected with backend's actual validation message; duplicate email rejected.
- Login: valid credentials succeed and populate `AuthContext`; invalid credentials show backend error; inactive account handled per whatever the backend actually returns (confirm this, don't assume a message).
- Session restoration: reloading the app with a valid stored access token calls `/auth/me` and restores state; with an invalid/expired token, session is cleared and user is redirected to `/login`.
- Refresh: a 401 on any authenticated request triggers exactly one refresh call even if multiple requests failed simultaneously; the original request(s) retry after refresh succeeds.
- Logout / logout-all: tokens and context state are cleared; subsequent authenticated requests correctly redirect to login.
- Protected/Admin routes: unauthenticated users are redirected from `ProtectedRoute`; non-admin users are redirected from `AdminRoute`; only `admin`/`user` roles are ever checked anywhere in the app.
- Regression: existing Phase 3 prediction upload UI still renders and functions (no auth wiring added to it in this phase).

## Edge Cases

- Refresh token expired/revoked while access token is still valid but the next request 401s — expect a clean logout, not an error loop.
- Multiple tabs/requests firing simultaneously that all hit 401 at once.
- Backend returns 422 with field-level `errors` for register — must render field-level errors where the UI supports it, not just a generic message.
- User navigates directly to a protected URL with no session — should not flash protected content before redirecting (respect `isLoading`).

## Definition of Done

- [ ] No mock/localStorage-simulated authentication remains in the active code path.
- [ ] All auth types match the confirmed backend schemas exactly; no invented roles or fields remain in `UserRole`/`User`.
- [ ] Login, register, refresh, logout, logout-all, and `/auth/me` are all integrated against the real backend.
- [ ] Token refresh works with no infinite loops and no duplicate concurrent refresh calls.
- [ ] Session restoration on app load uses `/auth/me`, not a mock session blob.
- [ ] Route guards only reason about `admin`/`user`.
- [ ] Existing component structure, provider setup, and folder architecture are unchanged except where explicitly required above.
- [ ] Loading, error, and success states are implemented for every auth interaction.
- [ ] No fake data, no invented endpoints, no invented error copy beyond what the backend actually returns.
- [ ] Phase 3 prediction upload UI is untouched and still functions.

## Explicitly Do NOT Implement

- Real prediction submission or `/predictions` integration (Phase 5).
- Prediction history (Phase 6).
- Reports/analytics (Phase 7).
- Admin user management data screens (Phase 8).
- System/monitoring screens (Phase 9).
- Any role beyond `admin`/`user`.
- Any forgot-password/reset-password/verify-email backend call not confirmed to exist in the current backend source.

## Final Instruction

Before writing any code, inspect the current frontend files listed above and the backend's `app/services/auth_service.py` and `app/dependencies/auth.py` to confirm exact error behavior. Modify only what is necessary to complete this phase. Do not rewrite working architecture. Do not invent APIs or fields. Do not use fake data. After implementation, report exactly which files were changed, any assumptions made (especially around error-status-code behavior if it could not be fully confirmed), and stop — do not proceed to Phase 5 automatically.