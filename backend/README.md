# OncoVision AI — Backend

Enterprise-grade AI Medical Imaging Platform backend for Lung & Colon Cancer Histopathology Image Classification, built with FastAPI, PostgreSQL, and TensorFlow/Keras.

> **Current status: Phase 10 — Production Polish & Final Backend Hardening.** All planned backend subsystems are implemented: authentication, AI model infrastructure, the prediction pipeline, prediction history, reporting, administration, and monitoring. The project remains **UNDER DEVELOPMENT** and is not a production-deployed system;

📄 See also: [Project README](../README.md) · [Frontend README](../Frontend/README.md)

---

## Table of Contents

- [Project Overview](#project-overview)
- [Technology Stack](#technology-stack)
- [Architecture](#architecture)
- [Folder Structure](#folder-structure)
- [Global Response Format](#global-response-format)
- [API Endpoints](#api-endpoints)
- [AI Model Infrastructure](#ai-model-infrastructure)
- [Prediction Pipeline](#prediction-pipeline)
- [Prediction History](#prediction-history)
- [Reporting](#reporting)
- [Administration](#administration)
- [Monitoring](#monitoring)
- [Authentication & Authorization](#authentication--authorization)
- [Running Locally](#running-locally)
- [Environment Variables](#environment-variables)
- [Database Migrations](#database-migrations)
- [Docker](#docker)
- [Testing](#testing)
- [API Documentation](#api-documentation)
- [Development Progress](#development-progress)

---

## Project Overview

OncoVision AI supports:

- ✅ JWT authentication & role-based authorization (Standard User / Administrator)
- ✅ Centralized Model Manifest & Registry (Hugging Face Hub–backed, checksum-verified)
- ✅ Memory-aware, fault-tolerant AI Runtime Manager (hybrid startup/lazy loading)
- ✅ Per-model AI inference (Prediction Engine) — sequential execution to bound peak memory
- ✅ Adaptive weighted ensemble prediction with confidence calibration and agreement scoring
- ✅ Immutable, append-only, user-scoped Prediction History with pagination, filtering, and detail retrieval
- ✅ Prediction Analytics, CSV export, and PDF report generation
- ✅ Administration: user management, prediction/history oversight, system status
- ✅ Runtime/application/database monitoring, isolated from the core prediction pipeline
- ✅ Dockerized deployment (multi-stage, non-root, healthchecked) targeting Render + Neon PostgreSQL
- ✅ Centralized exception handling and a consistent global API response envelope
- ✅ OpenAPI/Swagger documentation for every endpoint

## Technology Stack

**Backend**
- Python 3.10 (Docker runtime) / FastAPI
- Pydantic & Pydantic Settings
- SQLAlchemy (async) + Alembic
- PostgreSQL (Neon in production)
- PyJWT + Passlib/bcrypt
- TensorFlow / Keras (2.10)
- NumPy, OpenCV/Pillow
- Hugging Face Hub (model storage/download)
- ReportLab (PDF generation)

**Deployment**
- Backend: Render
- Database: Neon PostgreSQL
- Model storage: Hugging Face Hub
- Containerization: Docker / Docker Compose

## Architecture

The backend follows layered Clean Architecture with a fully isolated Machine Learning subsystem. Routers never contain business logic, repositories never perform machine learning, and only the AI Runtime Manager may create TensorFlow model instances.

```
Frontend
   ↓
REST API (/api/v1) — FastAPI Routers (thin; auth, validation, delegation only)
   ↓
Application Services (business logic)
   ↓                                   ↓
Repositories ──► PostgreSQL           AI Runtime Layer
                  (Neon)                 ↓
                                       AI Runtime Manager (sole owner of TensorFlow instances)
                                          ↓
                                       Model Registry / Manifest (single source of truth)
                                          ↓
                                       Download Manager + Cache Manager ── Hugging Face Hub

Prediction Engine ──► Adaptive Ensemble Engine ──► Confidence Calibration
      (per-model inference)   (weighted voting,          ↓
                                agreement scoring)   Final Prediction Builder
                                                            ↓
                                                     Response Builder ──► API Response
                                                            ↓
                                                     Prediction History (immutable, append-only)
                                                            ↓
                                              Reporting / Analytics / CSV / PDF Export
```

Key architectural rules enforced throughout the codebase (see the project's Architecture Decision Records):

- Routers never contain business logic; business logic lives in Services. Database access lives only in Repositories.
- Only `AIRuntimeManager` may instantiate TensorFlow model objects. Every other component — including the Prediction Engine — only ever consumes already-loaded instances through it.
- No model path, weight, label, or preprocessing setting is ever hardcoded; everything is sourced from the Model Manifest (`app/ml/manifest/models.json`).
- The Prediction Engine produces only individual, per-model predictions and never performs ensemble voting; that is the Adaptive Ensemble Engine's responsibility.
- A single model failing to download, load, or infer never takes down the service — prediction continues using every model that succeeded.
- Prediction History is immutable and append-only; no code path modifies an existing record.
- Reporting, Analytics, CSV/PDF export, Administration, and Monitoring are all read-only with respect to AI inference — none of them execute predictions or load models.
- Every user-facing history/analytics/reporting operation is scoped to the authenticated user at the database query itself; ownership can never be bypassed via a filter or identifier.
- Administrative endpoints require server-side–enforced `Administrator` privileges; client-provided role claims are never trusted on their own — authorization is re-derived from the verified JWT on every request.

## Folder Structure

```
backend/
├── app/
│   ├── main.py                        # FastAPI application entry point
│   ├── core/
│   │   ├── config.py                   # Storage directory helpers
│   │   ├── settings.py                 # Environment-driven Settings model
│   │   ├── logging.py                  # Structured logging configuration
│   │   ├── exceptions.py               # Centralized exception types + handlers
│   │   ├── request_metrics.py          # In-memory request metrics store (Monitoring)
│   │   └── upload.py                   # Shared upload constants/helpers
│   ├── api/
│   │   ├── router.py                    # Aggregates every versioned sub-router
│   │   └── v1/
│   │       ├── health.py                 # GET /api/v1/health
│   │       ├── system.py                 # GET /api/v1/system, /system/models, /system/runtime, /system/models/status
│   │       ├── auth.py                   # POST/GET /api/v1/auth/*
│   │       ├── predictions/              # POST /api/v1/predictions
│   │       ├── history/                  # GET /api/v1/predictions/history, /predictions/history/{id}
│   │       ├── reports.py                # GET /api/v1/reports/*
│   │       ├── monitoring.py             # GET /api/v1/monitoring
│   │       └── admin/                    # /api/v1/admin/* — users, history, system
│   ├── middleware/                       # Request ID, logging, metrics, process-time, security headers
│   ├── models/                           # SQLAlchemy ORM models (User, RefreshToken, PredictionHistoryRecord, enums)
│   ├── repositories/                     # Database access layer — the only layer that queries PostgreSQL
│   ├── database/                         # Async SQLAlchemy engine, session, declarative base
│   ├── schemas/                          # Public Pydantic request/response contracts
│   ├── services/                         # Business logic: auth, JWT, password, prediction orchestration,
│   │                                      #   runtime adapter/validator/metadata, history, analytics, reports,
│   │                                      #   admin (users/history/system), monitoring
│   ├── history/                          # Prediction History domain module (filters, pagination, mapper, enums)
│   ├── reports/                          # Reporting subsystem: analytics, CSV export, PDF export
│   ├── monitoring/                       # Monitoring domain module (health, metrics, result contracts)
│   ├── admin/                            # Administration-specific exceptions
│   ├── ml/                               # AI / Machine Learning subsystem (isolated from API/DB layers)
│   │   ├── manifest/models.json           # Model Manifest — single source of truth for model metadata
│   │   ├── registry/                      # Manifest loading + validated, read-only registry access
│   │   ├── downloader/                    # Hugging Face Hub download + checksum verification
│   │   ├── cache/                         # Local on-disk model weight cache
│   │   ├── metadata/                      # Read-only manifest/registry/cache summaries for the API layer
│   │   ├── runtime/                       # AI Runtime Manager — sole owner of TensorFlow instances
│   │   ├── preprocessing/                 # Manifest-driven image preprocessing
│   │   ├── prediction/                    # Prediction Engine — per-model inference only
│   │   ├── ensemble/                      # Adaptive Ensemble Engine — voting, calibration, final prediction
│   │   └── response/                      # Response Builder — assembles the public prediction response
│   ├── utils/                             # Response envelope helpers, environment helpers, security helpers
│   ├── constants/                         # Static application constants (tags, prefixes, supported formats)
│   ├── dependencies/                      # FastAPI DI providers + auth/authorization dependencies
│   └── lifecycle/                         # Startup/shutdown lifespan logic
├── alembic/                              # Database migrations
├── storage/
│   ├── uploads/                           # Uploaded histopathology images (transient)
│   ├── reports/                           # Generated PDF reports (transient)
│   └── models/                            # Cached TensorFlow model weight files
├── tests/                                # Unit/service/API test suite, mirroring the app/ layout
├── requirements.txt                      # Production dependencies
├── requirements-dev.txt                  # Test-only dependencies (pytest)
├── Dockerfile
├── .dockerignore
├── .env.example
└── README.md
```

## Global Response Format

Every endpoint returns a consistent JSON envelope:

```json
{
  "success": true,
  "message": "Request completed successfully.",
  "data": {},
  "errors": null,
  "request_id": "b3f1c2a4-...",
  "timestamp": "2026-08-17T02:49:24.415566+00:00"
}
```

`success` is `false` and `data` is `null` on any error response; `errors` then carries structured details (e.g. per-field validation errors) where applicable. Internal exceptions are always logged server-side but never leak a stack trace or implementation detail into the response body.

## API Endpoints

All endpoints below are served under the `/api/v1` prefix unless noted.

### System

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | none | Application name, version, environment |
| GET | `/health` | none | Service health check |
| GET | `/system` | none | Application, runtime, and storage info |
| GET | `/system/models` | none | Registered model manifest summary (enabled models, cache availability) |
| GET | `/system/runtime` | none | AI Runtime Manager health snapshot (loaded/failed/pending models, memory status) |
| GET | `/system/models/status` | none | Per-model runtime lifecycle status |

### Authentication (`/auth`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/register` | none | Register a new user account |
| POST | `/auth/login` | none | Authenticate and receive an access/refresh token pair |
| POST | `/auth/refresh` | refresh token | Exchange a refresh token for a new token pair |
| POST | `/auth/logout` | access token | Revoke a single refresh token |
| POST | `/auth/logout-all` | access token | Revoke every refresh token for the current user |
| GET | `/auth/me` | access token | Get the currently authenticated user |

### Predictions

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/predictions` | access token | Submit a histopathology image for prediction |

Accepts a single image via `multipart/form-data` plus optional form fields: `confidence_threshold` (0.0–1.0, reliability flagging only, never alters inference), `include_individual_predictions`, `include_runtime_statistics`, `save_history`, `generate_report`. Runs centralized upload validation, verifies AI Runtime readiness, and executes sequential multi-model inference through the Prediction Engine → Adaptive Ensemble Engine → Confidence Calibration → Final Prediction Builder → Response Builder pipeline. Returns `503` if the AI Runtime has not finished initializing or has zero loaded models.

### Prediction History (`/predictions/history`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/predictions/history` | access token | One page of the authenticated user's prediction history, newest first |
| GET | `/predictions/history/{history_id}` | access token | Complete detail of a single history record owned by the caller |

Supports `page` / `page_size` pagination and optional filters (`status`, `predicted_class`, `start_date`, `end_date`, `min_confidence`, `max_confidence`), combined with logical AND. Ownership is enforced at the database query itself — a `history_id` owned by another user is indistinguishable from one that does not exist; both return `404`.

`status` values: `pending`, `success`, `partial_success`, `failed`.

### Reports (`/reports`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/reports/analytics` | access token | Aggregated prediction analytics for the authenticated user |
| GET | `/reports/export/csv` | access token | Streamed CSV export of the authenticated user's prediction history |
| GET | `/reports/export/pdf` | access token | Streamed PDF report of the authenticated user's prediction history |

Analytics returns the standard `APIResponse` JSON envelope; the CSV/PDF endpoints stream the raw file as the response body (`text/csv` / `application/pdf`) rather than wrapping it in the envelope. All three respect `Settings.REPORT_EXPORT_MAX_ROWS` / `REPORT_EXPORT_MAX_SIZE_BYTES` and return `413` if exceeded.

### Administration (`/admin`) — requires Administrator role

| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/users` | List registered users (paginated) |
| GET | `/admin/users/{user_id}` | Retrieve a single user's detail |
| POST | `/admin/users/{user_id}/activate` | Reactivate a user account |
| POST | `/admin/users/{user_id}/deactivate` | Deactivate a user account (last-administrator and self-deactivation protected) |
| GET | `/admin/history` | Prediction history across every user (optionally narrowed to one `user_id`) |
| GET | `/admin/history/{history_id}` | Detail of any user's prediction history record |
| GET | `/admin/system` | Aggregated application/database/runtime/model status snapshot |

Every admin endpoint requires a valid access token belonging to a user with the `admin` role; unauthenticated callers receive `401`, authenticated non-administrators receive `403`. Authorization is enforced entirely server-side.

### Monitoring (`/monitoring`) — requires Administrator role

| Method | Path | Description |
|--------|------|-------------|
| GET | `/monitoring` | Aggregated operational monitoring: application health, database connectivity, AI Runtime health, per-model availability, and request/prediction metrics |

Monitoring is strictly read-only, reuses existing runtime and prediction statistics rather than recalculating them, and a monitoring failure never affects prediction, history, or reporting requests.

## AI Model Infrastructure

### Model Manifest & Registry

Every production model is declared once in `app/ml/manifest/models.json` (id, version, framework, Hugging Face repository, filename, SHA-256 checksum, input size, class labels, ensemble weight, loading priority, enabled flag). `ModelRegistry` provides validated, read-only access to this data; nothing else in the codebase hardcodes model metadata.

Currently registered production models (5-class lung/colon histopathology classifier):

| Model | Priority | Loading Strategy | Ensemble Weight |
|---|---|---|---|
| MobileNetV2 | 1 | Startup | 0.30 |
| DenseNet121 | 2 | Startup | 0.33 |
| EfficientNetV2B0 + ResNet50 Feature Fusion | 3 | Lazy | 0.37 |

Class labels: `Colon Adenocarcinoma`, `Colon Benign Tissue`, `Lung Adenocarcinoma`, `Lung Benign Tissue`, `Lung Squamous Cell Carcinoma`.

`STARTUP_MODEL_LOAD_LIMIT` controls how many top-priority enabled models load eagerly at startup; the rest load lazily on first use.

### AI Runtime Manager

`AIRuntimeManager` is a process-wide singleton and the only component allowed to create TensorFlow model instances. It downloads (via Hugging Face Hub), checksum-verifies, caches, and loads models per the hybrid strategy above; tracks per-model lifecycle state (`registered → downloading → downloaded → loading → ready | failed | disabled`); and continues operating even if individual models fail to load or download — availability is prioritized over prediction completeness, per the memory-constrained (Render Free) deployment target.

### Model Storage & Caching

```
Hugging Face Hub → Model Downloader → Local Runtime Cache → AI Runtime Manager
```

Model weight files are never committed to the repository or stored in PostgreSQL. The backend downloads missing models, reuses cached models, avoids unnecessary redownloads, and validates every downloaded file's checksum before registering it with the runtime.

## Prediction Pipeline

```
Image Upload
   ↓
Image Validation (format, size, corruption, resolution bounds)
   ↓
Image Preprocessing (manifest-driven — resize, normalize, tensor conversion)
   ↓
Prediction Engine — sequential per-model inference via the AI Runtime Manager
   ↓
Adaptive Weighted Voting — 3 models → adaptive ensemble; 2 → weighted; 1 → single-model; 0 → failure
   ↓
Confidence Calibration — winning class, calibrated confidence, agreement ratio
   ↓
Final Prediction Builder
   ↓
Response Builder → API Response
   ↓
Prediction History (persisted after a successful response, never blocking it)
```

Every stage has a single responsibility and each is independently testable. A single model's inference failure is recorded and skipped — the response always reports which models succeeded and which failed, along with per-model and total inference timing.

## Prediction History

Prediction History is **immutable, append-only, and user-scoped**. It is completely independent from the AI inference pipeline: no history operation ever loads a model, runs inference, or recalculates a prediction. History persistence happens only after a prediction request has already completed successfully, and a persistence failure is logged but never fails the originating prediction response.

## Reporting

The Reporting subsystem — Prediction Analytics, CSV export, and PDF export — is built entirely on top of immutable Prediction History and is read-only with respect to the rest of the system: it never invokes AI inference and never modifies history. Reports and analytics are generated dynamically on each request rather than persisted.

## Administration

The Administration layer provides user management, account activation/deactivation, cross-user prediction/history oversight, and aggregated system status, all reusing the same services and repositories the user-facing APIs already use rather than duplicating business logic. It never manipulates TensorFlow models, Prediction Engine internals, or prediction history records directly.

## Monitoring

The Monitoring layer aggregates application health, database connectivity, AI Runtime health, and per-model availability from components that already compute this information — it introduces no duplicate metric calculations and no parallel health-check implementation. A monitoring failure is isolated and never affects prediction, history, or reporting requests.

## Authentication & Authorization

- JWT-based authentication (`HS256`), with separate, explicitly typed access and refresh tokens — a refresh token can never be used where an access token is expected, and vice versa.
- Access tokens are short-lived (`ACCESS_TOKEN_EXPIRE_MINUTES`, default 15 minutes); refresh tokens are longer-lived (`REFRESH_TOKEN_EXPIRE_DAYS`, default 30 days) and stored server-side as salted hashes, never in plaintext.
- Passwords are hashed with bcrypt (`BCRYPT_ROUNDS`, default 12).
- Two roles: `user` (Standard User) and `admin` (Administrator).
- Every protected endpoint depends on `get_current_active_user`; every admin-only endpoint additionally depends on `require_admin`. Role information is always re-derived from the verified JWT server-side — a client can never elevate its own privileges by sending a role claim.
- The application refuses to start with `APP_ENV=production` while `JWT_SECRET_KEY` is still set to its insecure development default.

## Running Locally

### Prerequisites

- Python 3.10+ (Docker image uses 3.10; a local virtualenv on a newer 3.x is also supported)
- A PostgreSQL database (e.g. Neon, or the `db` service in `docker-compose.yml`)

### Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then fill in DATABASE_URL, JWT_SECRET_KEY, etc.
```

### Run the server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API is served at `http://localhost:8000`. On startup, the AI Runtime Manager downloads (if not already cached) and loads the startup-priority models before the app begins serving traffic; a model that fails to load or download never prevents the application from starting — prediction-dependent endpoints simply operate with whatever models are available.

## Environment Variables

All configuration is sourced from environment variables (see `.env.example` for the full, current list). Key variables:

| Variable | Description | Default |
|---|---|---|
| `APP_NAME` | Application display name | `OncoVision AI Backend` |
| `APP_VERSION` | Application version | `1.0.0` |
| `APP_ENV` | Runtime environment (`development` \| `production`) | `development` |
| `DEBUG` | Enable debug mode | `false` |
| `HOST` / `PORT` | Bind host/port | `0.0.0.0` / `8000` |
| `API_PREFIX` | API version prefix | `/api/v1` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `MAX_UPLOAD_SIZE` | Max upload size in bytes | `10485760` |
| `MODEL_STORAGE_PATH` | Local cache path for downloaded model weight files | `storage/models` |
| `UPLOAD_PATH` / `REPORT_PATH` | Storage paths for uploads / generated reports | `storage/uploads` / `storage/reports` |
| `MODEL_MANIFEST_PATH` | Path to the Model Manifest JSON file | `app/ml/manifest/models.json` |
| `STARTUP_MODEL_LOAD_LIMIT` | Number of top-priority enabled models loaded eagerly at startup | `2` |
| `IMAGE_MIN_RESOLUTION` / `IMAGE_MAX_RESOLUTION` | Accepted uploaded image width/height bounds, in pixels | `32` / `4096` |
| `PREDICTION_HISTORY_LIST_LIMIT` | Internal upper bound on unbounded history queries | `200` |
| `REPORT_EXPORT_MAX_ROWS` | Max history rows per report/analytics/CSV/PDF export | `1000` |
| `REPORT_EXPORT_MAX_SIZE_BYTES` | Max generated export document size, in bytes | `5242880` |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins, or `*` | `*` |
| `DATABASE_URL` | Async PostgreSQL connection string | *(must be set)* |
| `JWT_SECRET_KEY` | Secret used to sign JWTs | *(must be set to a strong value in production)* |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime, in minutes | `15` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime, in days | `30` |
| `BCRYPT_ROUNDS` | Password hashing cost factor | `12` |

Supported uploaded image formats for prediction: **JPEG, JPG, PNG, TIFF**.

## Database Migrations

```bash
python -m alembic upgrade head
```

Migrations live under `alembic/versions/` as a single linear chain (no branching):

| Revision | Description |
|---|---|
| `0001_initial_auth_tables` | `users`, `refresh_tokens` |
| `0002_prediction_history_table` | `prediction_history` |

## Docker

### Build & run directly

```bash
cd backend
docker build -t oncovision-backend .
docker run -p 8000:8000 --env-file .env oncovision-backend
```

The image is a multi-stage build (compiler toolchain stays in the builder stage only), runs as a non-root user (`appuser`), and ships no `--reload` flag. A container `HEALTHCHECK` polls `GET /api/v1/health` every 30s (60s start period, 3 retries). Named volumes/bind mounts should back `storage/uploads`, `storage/reports`, and `storage/models` so downloaded model weights and generated artifacts survive container restarts.

### Docker Compose (backend + local PostgreSQL)

For local development/manual verification, `docker-compose.yml` (at the repository root) runs the backend alongside a disposable PostgreSQL container (`db`, `postgres:16-alpine`, healthchecked so the backend only starts once the database is ready). No additional infrastructure (Redis, Celery, etc.) is introduced — production targets Render (backend) + Neon PostgreSQL (database) directly. This is also how to run the **full stack** (backend + frontend + db) together — see the [root README](../README.md#docker-recommended) for the one-command version.

```bash
# from the repository root
cp backend/.env.example backend/.env   # first time only — fill in JWT_SECRET_KEY etc.
docker compose up --build backend db
docker compose exec backend python -m alembic upgrade head
```

The backend container is reachable at `http://localhost:8000` (`/docs` for Swagger UI). Model weights, uploads, reports, and logs persist in named volumes (`oncovision_models`, `oncovision_uploads`, `oncovision_reports`, `oncovision_logs`) defined in `docker-compose.yml`, so they survive `docker compose down` (but not `docker compose down -v`).

## Testing

```bash
pip install -r requirements.txt -r requirements-dev.txt
python -m compileall app tests
python -m pytest tests -v
```

Tests are organized to mirror `app/`: `tests/api`, `tests/services`, `tests/history`, `tests/reports`, `tests/monitoring`, `tests/admin`, `tests/ml`, `tests/middleware`. `requirements-dev.txt` is installed only for local development and CI, never inside the production Docker image.

## API Documentation

Once running, interactive API docs are available at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI schema: `http://localhost:8000/openapi.json`

## Development Progress

| Phase | Status |
|---|---|
| Phase 1 — Project Foundation | ✅ Complete |
| Phase 2 — Authentication & Database | ✅ Complete |
| Phase 3 — AI Core (Model Infrastructure, Runtime Manager, Prediction Engine, Adaptive Ensemble Engine) | ✅ Complete |
| Phase 4 — Prediction API | ✅ Complete |
| Phase 5 — Prediction History (persistence, retrieval, pagination & filtering, detail API) | ✅ Complete |
| Phase 6 — Reporting (analytics, CSV export, PDF export, reporting APIs) | ✅ Complete |
| Phase 7 — Administration & Governance | ✅ Complete |
| Phase 8 — Monitoring & Observability | ✅ Complete |
| Phase 9 — Deployment Optimization | ✅ Complete |
| Phase 10 — Production Polish & Final Backend Hardening | ✅ Complete |

**Next:** Frontend integration, end-to-end testing, and final project delivery.

---

*OncoVision AI remains under active development and is not represented as production-ready.*
