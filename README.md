# OncoVision AI

Enterprise-oriented AI-assisted histopathology image analysis platform for
**Lung & Colon Cancer** classification — a React 19 + TypeScript frontend
backed by a FastAPI + PostgreSQL + TensorFlow backend.

> **Status: under active development.** All planned backend subsystems
> (auth, AI inference, history, reporting, admin, monitoring) are complete;
> frontend integration and end-to-end testing are ongoing. This is a
> decision-support / research-oriented project — **not a diagnostic
> device**, not clinically validated, not production-deployed.

📄 Component docs: **[Frontend README](./Frontend/README.md)** · **[Backend README](./backend/README.md)**

---

## Table of contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [Repository layout](#repository-layout)
- [Quickstart](#quickstart)
- [Docker (recommended)](#docker-recommended)
- [Running each service manually](#running-each-service-manually)
- [Environment variables](#environment-variables)
- [API documentation](#api-documentation)
- [Testing](#testing)
- [Disclaimer](#disclaimer)

---

## Overview

OncoVision AI lets a user upload a histopathology image and get an
AI-assisted prediction across lung and colon tissue classes, backed by an
adaptive ensemble of TensorFlow models (MobileNetV2, DenseNet121, and an
EfficientNetV2B0+ResNet50 fusion model). It supports:

- JWT-based authentication with `user` / `admin` roles
- Multi-model ensemble prediction with confidence calibration and
  agreement scoring
- Immutable, user-scoped prediction history with pagination and filtering
- Analytics, CSV export, and PDF report generation
- Administration (user management, cross-user history/system oversight)
- Runtime, database, and application monitoring
- A React dashboard wired against the real backend for every feature above
  (demo-only pages are clearly labeled where no backend endpoint exists yet
  — see the [Frontend README](./Frontend/README.md#backend-integration-status))

## Architecture

```
┌─────────────────────────┐        HTTPS/JSON        ┌──────────────────────────────┐
│   Frontend (React SPA)   │ ───────────────────────► │   Backend (FastAPI, /api/v1) │
│   served by Nginx        │ ◄─────────────────────── │                               │
└─────────────────────────┘                           └───────────────┬───────────────┘
                                                                        │
                                              ┌─────────────────────────┼─────────────────────────┐
                                              ▼                         ▼                         ▼
                                        PostgreSQL              AI Runtime Manager          Storage volumes
                                     (users, history)      (TensorFlow model instances,   (uploads, reports,
                                                             Hugging Face Hub–backed)        cached model weights)
```

See the [Backend README](./backend/README.md#architecture) for the full
layered architecture (routers → services → repositories, and the isolated
ML subsystem) and the [Frontend README](./Frontend/README.md#project-structure)
for the frontend's folder structure.

## Tech stack

| Layer | Stack |
|---|---|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, shadcn/ui (Radix), TanStack Query, Axios, React Router, React Hook Form + Zod |
| Backend | Python 3.10, FastAPI, Pydantic, SQLAlchemy (async) + Alembic, PyJWT, TensorFlow/Keras 2.10, ReportLab |
| Database | PostgreSQL (Neon in production; `postgres:16-alpine` locally) |
| Model storage | Hugging Face Hub (checksum-verified downloads, on-disk cache) |
| Infra | Docker / Docker Compose, Nginx (frontend static serving), Render (backend deploy target) |

## Repository layout

```
OncoVision/
├── Frontend/            # React 19 + TypeScript SPA — see Frontend/README.md
├── backend/              # FastAPI + PostgreSQL + TensorFlow API — see backend/README.md
├── docker-compose.yml    # Full-stack local orchestration (db + backend + frontend)
└── README.md             # You are here
```

> Note the casing: the frontend directory is `Frontend/` (capital F), the
> backend directory is `backend/` (lowercase) — match it exactly on
> case-sensitive filesystems (Linux/Docker) and in `docker-compose.yml`.

## Quickstart

The fastest way to get the whole stack running locally is Docker Compose —
see [below](#docker-recommended). To run each service by hand instead (e.g.
for frontend-only UI work, or backend development without rebuilding a
container each time), see [Running each service
manually](#running-each-service-manually).

## Docker (recommended)

**Prerequisites:** Docker and Docker Compose.

```bash
# 1. Configure the backend environment
cp backend/.env.example backend/.env
# then edit backend/.env — at minimum set a real JWT_SECRET_KEY;
# DATABASE_URL already matches the docker-compose `db` service by default

# 2. Build and start everything (PostgreSQL + backend + frontend)
docker compose up --build

# 3. Run database migrations (first run only, in a second terminal)
docker compose exec backend python -m alembic upgrade head
```

| Service | URL | Notes |
|---|---|---|
| Frontend | http://localhost:3000 | Nginx-served static build |
| Backend API | http://localhost:8000 | Swagger UI at `/docs`, ReDoc at `/redoc` |
| PostgreSQL | `localhost:5432` | Ephemeral container, persisted via the `oncovision_pgdata` volume |

What `docker-compose.yml` sets up:

- **`db`** — `postgres:16-alpine`, with a healthcheck the `backend` service
  waits on before starting.
- **`backend`** — built from `backend/Dockerfile` (multi-stage, non-root
  runtime user, container healthcheck against `GET /api/v1/health`),
  reading config from `backend/.env`. Model weights, uploads, reports, and
  logs persist in named volumes so they survive `docker compose down`
  (but not `docker compose down -v`).
- **`frontend`** — built from `Frontend/Dockerfile` (Node build stage →
  static `dist/` served by `nginx:alpine`), started only after `backend`
  is up, exposed on host port `3000` (container port `80`).

To stop everything: `docker compose down` (add `-v` to also delete the
named volumes — this wipes the local database and cached model weights).

To rebuild a single service after code changes: `docker compose up --build backend` (or `frontend`).

For component-specific Docker details (build args, healthchecks, image
internals), see the [Backend Docker section](./backend/README.md#docker)
and [Frontend Docker section](./Frontend/README.md#docker).

## Running each service manually

For day-to-day development, running each service natively (with hot
reload) is usually faster than rebuilding containers. Full details,
including environment variables and scripts, are in each component's
README:

- **Backend** — Python 3.10+, a PostgreSQL instance (Docker's `db` service
  works fine), `pip install -r requirements.txt`, `uvicorn app.main:app
  --reload`. See the [Backend README](./backend/README.md#running-locally).
- **Frontend** — Node.js 18+, `npm install`, `npm run dev` (expects the
  backend reachable at `http://localhost:8000` by default). See the
  [Frontend README](./Frontend/README.md#getting-started).

## Environment variables

Each service owns its own configuration:

- **Backend** — see `backend/.env.example` and the [full table in the
  Backend README](./backend/README.md#environment-variables) (database URL,
  JWT secret, storage paths, upload limits, Hugging Face token, etc.).
- **Frontend** — a single `VITE_API_URL` (see the [Frontend
  README](./Frontend/README.md#environment-variables)); note it's baked in
  at **build time**, not read at container runtime.
- **`docker-compose.yml`** additionally reads `POSTGRES_USER` /
  `POSTGRES_PASSWORD` / `POSTGRES_DB` (from `backend/.env`, with
  `postgres`/`postgres`/`oncovision` defaults) to configure the local `db`
  service.

## API documentation

Once the backend is running, interactive docs are available at:

- Swagger UI — `http://localhost:8000/docs`
- ReDoc — `http://localhost:8000/redoc`
- OpenAPI schema — `http://localhost:8000/openapi.json`

## Testing

```bash
cd backend
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest tests -v
```

See the [Backend README](./backend/README.md#testing) for how the test
suite is organized. The frontend does not currently have an automated test
suite configured.

## Disclaimer

OncoVision AI is a research/decision-support project. Predictions are
AI-generated model output — labeled as such throughout the UI (e.g. "AI
Prediction", "Model Confidence") — and are never presented as a confirmed
diagnosis. It is not certified as a medical device and must not be used
for actual clinical decision-making.
