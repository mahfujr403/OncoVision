# OncoVision AI — Backend

Enterprise-grade AI Medical Platform backend for Lung & Colon Cancer Histopathology Image Classification.

> **Current status: Phase 4.5.4 — Prediction Service Runtime Integration complete.** Project foundation, authentication, database integration, the full AI model infrastructure (manifest, registry, runtime manager, prediction engine, adaptive ensemble engine), and the Prediction API's request/response contract, upload validation, and AI Runtime integration are implemented. The `POST /api/v1/predictions` endpoint validates AI Runtime readiness and returns a live runtime metadata snapshot, but does not yet run model inference or ensemble aggregation — see [Roadmap](#roadmap).

## Project Overview

OncoVision AI supports, or will support once all phases are complete:

- ✅ JWT Authentication & Role-Based Authorization
- ✅ Centralized Model Manifest & Registry (Hugging Face Hub–backed)
- ✅ Memory-aware, fault-tolerant AI Runtime Manager (hybrid startup/lazy loading)
- ✅ Individual per-model AI inference (Prediction Engine)
- ✅ Adaptive Ensemble Learning (engine implemented; not yet wired into the Prediction API)
- 🟡 Prediction API (`POST /api/v1/predictions`) — request/response contract, upload validation, and AI Runtime integration live; model inference and ensemble aggregation not yet connected
- ⬜ Prediction History
- ⬜ PDF Report Generation
- ⬜ Admin Dashboard & Monitoring
- ✅ Render-ready deployment configuration (Dockerfile, ephemeral-filesystem-aware model caching)

## Folder Structure

```
backend/
├── app/
│   ├── main.py                        # FastAPI application entry point
│   ├── core/
│   │   ├── config.py                   # Resolved settings + storage helpers
│   │   ├── settings.py                 # Environment-driven Settings model
│   │   ├── logging.py                  # Structured logging configuration
│   │   └── exceptions.py               # Centralized exception handlers
│   ├── api/
│   │   ├── router.py                    # Aggregates all versioned routers
│   │   └── v1/
│   │       ├── health.py                # GET /api/v1/health
│   │       ├── system.py                # GET /api/v1/system, /system/models, /system/runtime, /system/models/status
│   │       ├── auth.py                  # POST/GET /api/v1/auth/* — registration, login, refresh, logout, me
│   │       └── predictions/             # POST /api/v1/predictions
│   │           ├── router.py             # Endpoint definition; delegates to PredictionService only
│   │           ├── schemas.py            # Public request contract (ADR-012)
│   │           ├── responses.py          # Public response contract (ADR-012)
│   │           ├── validators.py         # Request-level validation helpers
│   │           ├── exceptions.py         # Upload-validation-failure API mappings
│   │           └── examples.py           # OpenAPI/Swagger response examples
│   ├── middleware/
│   │   ├── request_id.py                # X-Request-ID header
│   │   ├── logging.py                   # Request/response logging
│   │   ├── process_time.py              # X-Process-Time header
│   │   └── security_headers.py          # Security response headers
│   ├── models/                          # SQLAlchemy ORM models (User, RefreshToken, enums)
│   ├── repositories/                    # Database access layer (User, RefreshToken)
│   ├── database/                        # Async SQLAlchemy engine, session, declarative base
│   ├── schemas/
│   │   ├── common.py                     # Shared Pydantic schemas
│   │   ├── response.py                   # Standard API response envelope
│   │   ├── auth.py                       # Auth request/response schemas
│   │   └── user.py                       # User schemas
│   ├── services/
│   │   ├── system_service.py             # Application/system info logic
│   │   ├── auth_service.py               # Registration, login, refresh, logout logic
│   │   ├── jwt_service.py                # JWT issuing/verification
│   │   ├── password_service.py           # Password hashing/verification
│   │   ├── prediction_service.py         # Orchestrates the prediction pipeline (ADR-013)
│   │   ├── prediction_context.py         # PredictionContext / PredictionOptions (request-scoped state)
│   │   ├── prediction_result.py          # PredictionResult / pipeline stage bookkeeping
│   │   ├── prediction_exceptions.py      # Prediction pipeline exception types
│   │   ├── runtime_adapter.py            # RuntimeAdapter — sole PredictionService→AIRuntimeManager boundary (ADR-014)
│   │   ├── runtime_validator.py          # RuntimeValidator — pre-inference AI Runtime readiness gate (ADR-015)
│   │   └── runtime_metadata.py           # RuntimeMetadataService — runtime/manifest metadata snapshots (ADR-016)
│   ├── ml/                               # AI / Machine Learning subsystem (isolated from API/DB layers)
│   │   ├── schemas.py                     # ModelManifest / ModelManifestEntry / registry response schemas
│   │   ├── exceptions.py                  # Manifest, download, checksum, not-found exceptions
│   │   ├── manifest/
│   │   │   └── models.json                 # Model Manifest — single source of truth for model metadata
│   │   ├── registry/
│   │   │   ├── manifest_loader.py          # Loads, validates, and integrity-checks the manifest
│   │   │   └── model_registry.py           # Read-only, validated access to model metadata
│   │   ├── downloader/
│   │   │   ├── huggingface_downloader.py   # Downloads model weight files from Hugging Face Hub
│   │   │   └── download_manager.py         # Ensures a model file is present, cached, and checksum-verified
│   │   ├── cache/
│   │   │   └── cache_manager.py            # Local on-disk weight file cache (ephemeral-filesystem aware)
│   │   ├── metadata/
│   │   │   └── metadata_service.py         # Read-only manifest/registry/cache summaries for the API layer
│   │   ├── runtime/                        # AI Runtime Manager (ADR-007) — sole owner of TensorFlow instances
│   │   │   ├── runtime_manager.py           # AIRuntimeManager singleton — hybrid loading, lifecycle
│   │   │   ├── runtime_state.py             # Async-safe per-model lifecycle state store
│   │   │   ├── loader.py                    # Turns a cached weight file into a loaded Keras model
│   │   │   ├── memory_manager.py            # Memory estimation and availability checks
│   │   │   ├── warmup.py                    # Per-model warmup hook registry (extension point)
│   │   │   ├── health.py                    # Runtime health/status reporting
│   │   │   └── exceptions.py                # Runtime-not-initialized, load, unavailable errors
│   │   └── prediction/                     # Prediction Engine (ADR-008) — individual model inference only
│   │       ├── prediction_engine.py         # Orchestrates validation → preprocessing → per-model inference
│   │       ├── predictor.py                 # Runs inference for a single loaded model
│   │       ├── preprocessor.py              # Manifest-driven image preprocessing
│   │       ├── validator.py                 # Uploaded image validation
│   │       ├── confidence.py                # Reusable confidence/top-k calculation
│   │       ├── prediction_result.py         # Individual prediction / execution stats schemas
│   │       └── exceptions.py                # Validation, no-models-available, execution errors
│   │   └── ensemble/                       # Adaptive Ensemble Engine (ADR-009) — consumes Prediction Engine output only
│   │       ├── ensemble_engine.py           # AdaptiveEnsembleEngine — single/two/three-model strategy selection
│   │       ├── strategy.py                  # Strategy selection based on available model count
│   │       ├── weighted_voting.py           # Manifest-driven weighted voting
│   │       ├── confidence.py                # Ensemble confidence aggregation
│   │       ├── agreement.py                 # Inter-model agreement scoring
│   │       ├── decision.py                  # Final label decision logic
│   │       ├── response.py                  # EnsemblePredictionResult / AgreementLevel / EnsembleStrategyType
│   │       └── exceptions.py                # Ensemble-unavailable errors
│   ├── utils/
│   │   ├── environment.py                   # Timestamp, UUID, unit helpers
│   │   ├── response.py                       # success_response / error_response
│   │   └── security.py                       # Security-related helpers
│   ├── constants/
│   │   └── app.py                            # Static application constants
│   ├── dependencies/
│   │   ├── services.py                       # FastAPI DI providers for every service/manager
│   │   └── auth.py                           # Authentication/authorization dependencies
│   └── lifecycle/
│       ├── startup.py                        # Startup lifespan logic (incl. AI Runtime initialization)
│       └── shutdown.py                       # Shutdown lifespan logic
├── alembic/                              # Database migrations
├── storage/
│   ├── uploads/                           # Uploaded histopathology images (future)
│   ├── reports/                           # Generated PDF reports (future)
│   └── models/                            # Cached TensorFlow model weight files
├── tests/
├── requirements.txt
├── Dockerfile
├── .dockerignore
├── .env.example
└── README.md
```

## Architecture

The backend follows layered Clean Architecture with a fully isolated Machine Learning subsystem:

```
Frontend
   ↓
REST API (FastAPI Routers)
   ↓
Application Services ── PredictionService orchestrates the pipeline (ADR-013)
   ↓                        ↓
Repositories ──► Database   RuntimeAdapter ── sole PredictionService→AI Runtime boundary (ADR-014)
   (PostgreSQL / Neon)         ↓
                              AI Runtime Manager (app/ml/runtime) ── sole owner of TensorFlow model instances
                                 ↓
                              Model Registry / Manifest (app/ml/registry) ── single source of truth for model metadata
                                 ↓
                              Download Manager + Cache Manager ── Hugging Face Hub

Prediction Engine (app/ml/prediction) ──► Adaptive Ensemble Engine (app/ml/ensemble)
   (per-model inference, not yet wired         (weighted voting / agreement / decision,
    into the Prediction API)                    not yet wired into the Prediction API)
```

Key architectural rules enforced throughout the codebase (see `Architecture_Decision_Records`):

- Routers never contain business logic; business logic lives in Services. `PredictionService` is the single orchestration point for the prediction pipeline (ADR-013).
- Repositories never perform machine learning; ML modules never talk to the database.
- Only `AIRuntimeManager` may instantiate TensorFlow model objects (ADR-007). Every other component — including the Prediction Engine — only ever consumes already-loaded instances through it.
- `PredictionService` never talks to `AIRuntimeManager` or `ModelRegistry` directly; it depends only on `RuntimeAdapter`, a metadata-only abstraction (ADR-014), through `RuntimeValidator` (pre-inference readiness gating, ADR-015) and `RuntimeMetadataService` (runtime/manifest metadata snapshots, ADR-016).
- No model path, weight, label, or preprocessing setting is ever hardcoded; everything is sourced from the Model Manifest (ADR-006).
- The Prediction Engine produces only individual, per-model predictions and never performs ensemble voting (ADR-008); that is the Adaptive Ensemble Engine's responsibility (ADR-009).
- A single model failing to load or infer never takes down the service — the application/prediction continues with whatever models are available (ADR-005).

## Global Response Format

Every endpoint returns a consistent JSON envelope:

```json
{
  "success": true,
  "message": "Request completed successfully.",
  "data": {},
  "errors": null,
  "request_id": "b3f1c2a4-...",
  "timestamp": "2026-07-16T05:31:00+00:00"
}
```

## API Endpoints

| Method | Path                        | Description                                                              |
|--------|-----------------------------|----------------------------------------------------------------------------|
| GET    | `/`                          | Application name, version, environment                                     |
| GET    | `/api/v1/health`             | Service health check                                                        |
| GET    | `/api/v1/system`             | Application, runtime, and storage info                                     |
| GET    | `/api/v1/system/models`      | Registered model manifest summary (enabled models, cache availability)     |
| GET    | `/api/v1/system/runtime`     | AI Runtime Manager health (loaded/failed/pending models, memory status)    |
| GET    | `/api/v1/system/models/status`| Per-model runtime lifecycle status                                        |
| POST   | `/api/v1/auth/register`      | Register a new user account                                                |
| POST   | `/api/v1/auth/login`         | Authenticate and receive an access/refresh token pair                      |
| POST   | `/api/v1/auth/refresh`       | Exchange a refresh token for a new token pair                              |
| POST   | `/api/v1/auth/logout`        | Revoke a single refresh token                                              |
| POST   | `/api/v1/auth/logout-all`    | Revoke all refresh tokens for the current user                             |
| GET    | `/api/v1/auth/me`            | Get the currently authenticated user                                       |
| POST   | `/api/v1/predictions`        | Submit a histopathology image for prediction (upload validation + AI Runtime readiness only — see below) |

> `POST /api/v1/predictions` accepts a multipart image upload plus optional control flags (`confidence_threshold`, `include_individual_predictions`, `include_runtime_statistics`, `save_history`, `generate_report`). It runs centralized upload validation (ADR-011) and, when `include_runtime_statistics=true`, validates AI Runtime readiness and returns a live runtime metadata snapshot (loaded/failed models, manifest version). Model inference (`PredictionEngine`) and ensemble aggregation (`AdaptiveEnsembleEngine`) are implemented as standalone modules but not yet wired into this endpoint — `result` and `individual_predictions` are still returned as `null`. Requests are rejected with `503` if the AI Runtime has not finished initializing or has zero loaded models.

## AI Model Infrastructure

### Model Manifest & Registry
Every production model is declared once in `app/ml/manifest/models.json` (id, version, framework, Hugging Face repository, filename, SHA-256 checksum, input size, class labels, ensemble weight, loading priority, enabled flag). The `ModelRegistry` provides validated, read-only access to this data; nothing else in the codebase hardcodes model metadata. Currently registered:

| Model | Priority | Loading Strategy |
|---|---|---|
| EfficientNetV2B0 + ResNet50 Feature Fusion | 1 | Lazy |
| DenseNet121 | 2 | Startup |
| MobileNetV2 | 3 | Startup |

(`STARTUP_MODEL_LOAD_LIMIT` controls how many top-priority enabled models load eagerly at startup; the rest load lazily on first use.)

### AI Runtime Manager
`AIRuntimeManager` is a process-wide singleton and the only component allowed to create TensorFlow model instances. It downloads (via Hugging Face Hub), checksum-verifies, caches, and loads models according to the hybrid strategy above, tracks per-model lifecycle state (`registered → downloading → downloaded → loading → ready | failed | disabled`), and continues operating even if individual models fail to load, per the platform's memory-constrained (Render Free) deployment target.

### Prediction Engine
`PredictionEngine` (Phase 3.3) validates an uploaded image, preprocesses it once per distinct model input size (per the manifest), and runs inference independently against every currently loaded model via the Runtime Manager. It returns individual per-model predictions plus execution statistics — no ensemble aggregation. A single model's inference failure is recorded and skipped; the rest of the loaded models still return results.

### Adaptive Ensemble Engine
`AdaptiveEnsembleEngine` (Phase 3.4) consumes the individual predictions produced by the Prediction Engine and combines them via adaptive weighted voting, automatically selecting a single-model, two-model, or three-model strategy depending on how many models are currently available (ADR-009). It is fully implemented and unit-tested but not yet invoked by the Prediction API.

### Prediction Service & AI Runtime Integration
`PredictionService` (Phase 4.4–4.5.4) is the single orchestration point behind `POST /api/v1/predictions` (ADR-013). It runs upload validation, builds a `PredictionContext`, and — as of Phase 4.5.4 — validates AI Runtime readiness and collects a runtime metadata snapshot before allowing the pipeline to proceed:

- `RuntimeValidator.validate_or_raise()` (ADR-015) halts the request with a `503` if the AI Runtime hasn't finished initializing or has zero loaded models.
- `RuntimeMetadataService.collect()` (ADR-016) then assembles a point-in-time snapshot of loaded/failed/lazy models, manifest version, and framework list.
- Both collaborators talk to the AI Runtime Manager only through `RuntimeAdapter` (ADR-014) — `PredictionService` never holds a direct reference to `AIRuntimeManager` or `ModelRegistry`.

Preprocessing, per-model inference, and ensemble aggregation are still logged, recorded pipeline placeholders — see [Roadmap](#roadmap).

## Running Locally

### Prerequisites

- Python 3.11+
- A PostgreSQL database (e.g. Neon)

### Setup

```bash
cd backend
python -m venv venv
.\venv\Scripts\activate.ps1       # Mac: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### Database migrations

```bash
alembic upgrade head
```

### Run the server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`. On startup, the AI Runtime Manager downloads (if not already cached) and loads the startup-priority models before the app begins serving traffic; a model that fails to load never prevents startup.

## Environment Setup

All configuration is sourced from environment variables (see `.env.example`):

| Variable                     | Description                                                     | Default                                    |
|-------------------------------|-------------------------------------------------------------------|----------------------------------------------|
| `APP_NAME`                    | Application display name                                          | `OncoVision AI Backend`                      |
| `APP_VERSION`                 | Application version                                                | `1.0.0`                                      |
| `APP_ENV`                     | Runtime environment                                                | `development`                                |
| `DEBUG`                       | Enable debug mode                                                  | `false`                                      |
| `HOST`                        | Bind host                                                          | `0.0.0.0`                                    |
| `PORT`                        | Bind port                                                          | `8000`                                       |
| `API_PREFIX`                  | API version prefix                                                 | `/api/v1`                                    |
| `LOG_LEVEL`                   | Logging level                                                      | `INFO`                                       |
| `MAX_UPLOAD_SIZE`             | Max upload size in bytes (also enforced on prediction image uploads) | `10485760`                                |
| `MODEL_STORAGE_PATH`          | Local cache path for downloaded model weight files                | `storage/models`                             |
| `UPLOAD_PATH`                 | Path for uploaded images                                           | `storage/uploads`                            |
| `REPORT_PATH`                 | Path for generated PDF reports                                     | `storage/reports`                            |
| `MODEL_MANIFEST_PATH`         | Path to the Model Manifest JSON file                                | `app/ml/manifest/models.json`               |
| `STARTUP_MODEL_LOAD_LIMIT`    | Number of top-priority enabled models loaded eagerly at startup     | `2`                                           |
| `IMAGE_MIN_RESOLUTION`        | Minimum accepted uploaded image width/height, in pixels             | `32`                                          |
| `IMAGE_MAX_RESOLUTION`        | Maximum accepted uploaded image width/height, in pixels             | `4096`                                        |
| `ALLOWED_ORIGINS`             | Comma-separated CORS origins, or `*`                                | `*`                                            |
| `DATABASE_URL`                | Async PostgreSQL connection string                                  | *(none — must be set)*                        |
| `JWT_SECRET_KEY`               | Secret used to sign JWTs                                            | *(none — must be set in production)*         |
| `JWT_ALGORITHM`                | JWT signing algorithm                                               | `HS256`                                       |
| `ACCESS_TOKEN_EXPIRE_MINUTES`  | Access token lifetime, in minutes                                    | `15`                                          |
| `REFRESH_TOKEN_EXPIRE_DAYS`    | Refresh token lifetime, in days                                      | `30`                                          |
| `BCRYPT_ROUNDS`                | Password hashing cost factor                                         | `12`                                           |

Supported uploaded image formats for prediction: **JPEG, JPG, PNG, TIFF**.

## Docker

### Build

```bash
docker build -t oncovision-backend .
```

### Run

```bash
docker run -p 8000:8000 --env-file .env oncovision-backend
```

### Run with Docker Compose (backend + local PostgreSQL)

For local development/manual verification, `docker-compose.yml` runs the
backend alongside a disposable PostgreSQL container (no other services are
introduced -- production still targets Render + Neon PostgreSQL per
ADR-043):

```bash
cp .env.example .env   # first time only
docker compose up --build
```

Run migrations against the Compose-managed database once the containers are up:

```bash
docker compose exec backend python -m alembic upgrade head
```

The backend container publishes a Docker `HEALTHCHECK` against
`GET /api/v1/health`, so `docker compose ps` / `docker ps` reflect real
service readiness rather than just "container is running".

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
| Phase 3.1 — AI Model Infrastructure (Manifest, Registry, Downloader, Cache) | ✅ Complete |
| Phase 3.2 — AI Runtime Manager | ✅ Complete |
| Phase 3.3 — Prediction Engine | ✅ Complete |
| Phase 3.4 — Adaptive Ensemble Engine | ✅ Complete |
| Phase 4.1 — Prediction Route | ✅ Complete |
| Phase 4.2 — Upload Validation | ✅ Complete |
| Phase 4.3 — Request/Response Schema | ✅ Complete |
| Phase 4.4 — Prediction Service Skeleton | ✅ Complete |
| Phase 4.5.1 — Runtime Adapter | ✅ Complete |
| Phase 4.5.2 — Runtime Validation | ✅ Complete |
| Phase 4.5.3 — Runtime Metadata | ✅ Complete |
| Phase 4.5.4 — Prediction Service Runtime Integration | ✅ Complete |
| Phase 4.6 — Prediction Engine Integration | ⬜ Not started |
| Phase 4.7 — Ensemble Integration | ⬜ Not started |
| Phase 4.8 — Global Error Handling | ⬜ Not started |
| Phase 4.9 — OpenAPI Documentation | ⬜ Not started |
| Phase 4.10 — Final API Verification | ⬜ Not started |
| Phase 5 — Prediction History | ⬜ Not started |
| Phase 6 — Reports | ⬜ Not started |
| Phase 7 — Admin APIs | ⬜ Not started |
| Phase 8 — Monitoring | ⬜ Not started |
| Phase 9 — Deployment Optimization | ⬜ Not started |
| Phase 10 — Production Polish | ⬜ Not started |

## Roadmap

Next up is **Phase 4.6 — Prediction Engine Integration**, which wires the already-implemented `PredictionEngine` into `PredictionService` so `POST /api/v1/predictions` runs real per-model inference against every currently loaded model. After that: Phase 4.7 connects the `AdaptiveEnsembleEngine` to produce a final ensembled prediction; Phase 4.8–4.10 round out global error handling, OpenAPI documentation, and final API verification; then prediction history persistence, PDF report generation, an admin dashboard, production monitoring, and final Render deployment optimization and polish.

