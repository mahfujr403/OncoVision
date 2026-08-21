# OncoVision AI — Frontend

Enterprise-oriented AI-assisted histopathology image analysis platform for
Lung & Colon Cancer classification. React 19 + TypeScript frontend, built
against a real FastAPI backend.

> **Status: under active development.** Not clinically validated, not a
> diagnostic tool, not production-ready. See [Backend integration
> status](#backend-integration-status) below for exactly what is and isn't
> wired to real data.

---

## Tech stack

- React 19, TypeScript, Vite
- Tailwind CSS, shadcn/ui (Radix primitives), Framer Motion
- TanStack Query (server state), Axios (HTTP)
- React Router
- React Hook Form + Zod
- Lucide React, Sonner (toasts), React Dropzone

No Redux, no additional state-management library.

---

## Getting started

### Prerequisites

- Node.js 18+
- The OncoVision AI backend running locally (FastAPI, default
  `http://localhost:8000`) — this frontend has no standalone/offline mode
  for real data; pages backed by the backend will show error/empty states
  without it.

### Install & run

```bash
npm install
cp .env.example .env   # if present; otherwise create .env (see below)
npm run dev
```

The dev server runs on `0.0.0.0` (configurable via `PORT`, default from
`vite.config.ts`).

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000/api/v1` | Base URL for all backend API calls |

### Scripts

| Command | Purpose |
|---|---|
| `npm run dev` | Start the Vite dev server |
| `npm run build` | Production build |
| `npm run preview` | Preview a production build locally |
| `npm run format` | Format source with oxfmt |

---

## Project structure

```
src/
├── api/               # Axios instance, interceptors, envelope unwrap helper,
│                       # api/services/* (one file per backend resource)
├── components/         # Shared UI primitives (shadcn-style) + navigation
├── constants/          # api.ts (endpoint map), app.ts, roles.ts, routes.ts
├── contexts/            # AuthContext (real session state)
├── features/            # Feature-scoped code — auth/, prediction/
├── hooks/               # useAuth, usePagination, useSearch, queries/*
├── layouts/              # AuthLayout, LandingLayout, DashboardLayout, etc.
├── pages/                # Route-level page components (auth/, dashboard/, admin/, landing/)
├── providers/            # App-wide providers (QueryClient, Theme, Auth)
├── routes/               # Route table + guards (ProtectedRoute, AdminRoute, PublicRoute)
├── types/                # index.ts — real backend-contract types + demo-only types
└── utils/                # formatters, validation schemas, permissions
```

Feature-specific UI lives inside its feature folder (`features/auth`,
`features/prediction`); avoid dumping feature logic into generic
`components/`.

---

## Backend integration status

Every API call in this codebase is verified against the actual backend
source (routers, Pydantic schemas, the model manifest) rather than
assumed. `src/types/index.ts` documents the exact backend schema each type
mirrors. Two tiers:

### ✅ Real — wired to live backend endpoints

| Feature | Endpoint(s) |
|---|---|
| Register / Login / Session restore / Logout / Logout-all | `POST /auth/register`, `/login`, `GET /auth/me`, `POST /auth/logout(-all)` |
| Predict | `POST /predictions` (multipart) |
| Prediction History (list + detail) | `GET /predictions/history[/​{id}]` |
| Reports & Analytics (+ CSV/PDF export) | `GET /reports/analytics`, `/reports/export/csv`, `/reports/export/pdf` |
| Admin — Users (list, activate, deactivate) | `GET /admin/users`, `POST /admin/users/{id}/activate|deactivate` |
| Admin — System Health | `GET /monitoring`, `GET /admin/system` |
| Admin — Analytics | `GET /reports/analytics` + `GET /admin/users` + `GET /monitoring` (combined) |
| Admin — Model Registry | `GET /system/models` |

Token refresh uses a single-flight + request-queue pattern (no duplicate
`/auth/refresh` calls, no infinite loop; session is cleared and the user is
redirected to `/login` if refresh fails).

### 🧪 Demo only — no backend endpoint exists yet

These pages are **kept in the app and clearly labeled**, not deleted —
each renders a `<DemoDataBanner />` explaining exactly what's missing.
Do not treat their content as real.

- Benchmark, Comparison, Favorites, Notifications, Saved Cases
- Admin Audit Logs
- Forgot Password, Reset Password, Verify Email, Change Password (the
  backend has no password-reset, email-verification, or
  profile/password-update endpoints today — forms explain this rather than
  faking success)
- Profile editing (viewing is real via `GET /auth/me`; there is no
  profile-update endpoint to save to)

If you add the corresponding backend endpoint later, replace the relevant
service in `src/api/services/` and remove the `<DemoDataBanner />` from
that page — the UI shell is already there.

### Known backend constraints reflected in the UI

- Roles are **only** `admin` / `user` (see `src/constants/roles.ts`) — no
  researcher/doctor/viewer tier exists.
- `GET /admin/users` supports only `page`/`page_size` — no server-side
  search or filter, so Admin Users filters client-side on the loaded page.
- Upload accepts **JPEG, PNG, TIFF only, max 10 MB** (`src/constants/app.ts`).
- `confidence_threshold` on `POST /predictions` only flags results for
  review — it never changes model output.
- `generate_report` is accepted by `POST /predictions` for contract
  stability but not yet acted on by the backend; the UI marks it "Coming
  soon" rather than pretending it works.
- The real model manifest has exactly 3 models (MobileNetV2, DenseNet121,
  EfficientNetV2B0+ResNet50 fusion) and 5 class labels — see
  `KNOWN_CLASS_LABELS` in `src/constants/app.ts`.

---

## Adding a new backend-integrated feature

Follow the existing pattern rather than starting from UI assumptions:

1. Read the actual backend router + Pydantic schema for the endpoint.
2. Add/extend the matching type in `src/types/index.ts`.
3. Add a service function in `src/api/services/`.
4. Add a TanStack Query hook in `src/hooks/queries/`.
5. Build the page/component, reusing existing UI primitives
   (`components/ui/*`) and loading/empty/error patterns.
6. If the feature only partially exists on the backend, keep the rest
   visible behind `<DemoDataBanner feature="..." />` instead of removing
   it.

---

## Medical / UX copy discipline

Never imply definitive diagnosis. Use "AI Prediction", "Predicted Class",
"Model Confidence", "Model Agreement", "AI-assisted analysis" — never
"Diagnosis confirmed" or similar. This is a decision-support, research-
oriented platform, not a diagnostic device.
