<div align="center">

# 🔬 OncoVision AI
### Enterprise Histopathology Cancer Classification & AI Clinical Knowledge Assistant

[![Status](https://img.shields.io/badge/Status-Live%20Demo-00C7B7?style=for-the-badge&logo=statuspage&logoColor=white)](https://oncovision-live.netlify.app/)
[![Frontend](https://img.shields.io/badge/Frontend-Netlify-00AD9F?style=for-the-badge&logo=netlify&logoColor=white)](https://oncovision-live.netlify.app/)
[![Backend](https://img.shields.io/badge/Backend-Render-46E3B7?style=for-the-badge&logo=render&logoColor=black)](https://oncovision-backend-mp8n.onrender.com/docs)
[![Database](https://img.shields.io/badge/Database-Neon%20PostgreSQL-00E599?style=for-the-badge&logo=postgresql&logoColor=white)](https://neon.tech)
[![AI Core](https://img.shields.io/badge/AI%20Core-TensorFlow%202.10-FF6F00?style=for-the-badge&logo=tensorflow&logoColor=white)](https://huggingface.co)
[![LLM & RAG](https://img.shields.io/badge/LLM%20%26%20RAG-Google%20Gemini-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://aistudio.google.com)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)

<br/>

[![React](https://img.shields.io/badge/React-19.0-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![pgvector](https://img.shields.io/badge/pgvector-Vector%20Similarity-336791?style=flat-square&logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Vite](https://img.shields.io/badge/Vite-6.x-646CFF?style=flat-square&logo=vite&logoColor=white)](https://vitejs.dev)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.x-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)

</div>

Enterprise-oriented AI-assisted histopathology image analysis platform for
**Lung & Colon Cancer** classification and **AI Clinical Knowledge Assistant** — a React 19 + TypeScript frontend
backed by a FastAPI + PostgreSQL (`pgvector`) + TensorFlow + Google Gemini LLM backend.

> **Status: live.** This is a decision-support / research-oriented project
> — **not a diagnostic device**, not clinically validated. It's deployed
> as a **free-tier live demo** (see below), not a production-grade
> deployment.

📄 Component docs: **[Frontend README](./Frontend/README.md)** · **[Backend README](./backend/README.md)**

## 🔗 Live demo

| Service | Provider (free tier) | URL |
|---|---|---|
| Frontend | Netlify | [`https://oncovision-live.netlify.app`](https://oncovision-live.netlify.app/) |
| Backend API | Render | [`https://oncovision-backend-mp8n.onrender.com`](https://oncovision-backend-mp8n.onrender.com) — Swagger docs at `/docs` |
| Database | Neon (PostgreSQL + pgvector, serverless) | internal — not publicly exposed |
| Model storage | Hugging Face Hub | internal — pulled by the backend at runtime |
| LLM & RAG | Google Gemini AI | Google GenAI SDK (`gemini-3.5-flash-lite`, `gemini-embedding-2`) |

> **Free-tier heads-up:** the Render backend spins down after periods of
> inactivity. The **first request after idle time can take 30–60+ seconds**
> (cold start + model load) before it responds — this is expected, not a
> bug. Subsequent requests are fast until it idles out again.

---

## Table of contents

- [Live demo](#-live-demo)
- [Overview](#overview)
- [Key Features](#key-features)
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

OncoVision AI lets clinicians and researchers upload histopathology images and receive
calibrated, multi-model ensemble predictions across 5 lung and colon tissue classes, alongside
an **AI-powered clinical assistant** providing on-demand prediction summaries, case-specific Q&A, and RAG-driven oncology education.

### Key Features

- **Multi-Model Ensemble Prediction**: Adaptive ensemble combining MobileNetV2, DenseNet121, and an EfficientNetV2B0+ResNet50 feature fusion model (up to 99.99% benchmark accuracy), with confidence calibration and model agreement scoring.
- **AI Clinical Summary**: On-demand, concise AI-generated explanations of histopathology findings directly inside prediction details, persisted and cached in PostgreSQL.
- **Context-Aware Prediction Chat**: Interactive multi-turn chat anchored to an individual prediction, explaining model consensus, class probabilities, and histopathological nuances.
- **RAG Knowledge Assistant**: Retrieval-Augmented Generation using Google Gemini embeddings (`gemini-embedding-2`) and PostgreSQL `pgvector` cosine similarity search over a curated oncology knowledge base (covering colon/lung cancer, cellular morphology, H&E staining, and platform architecture).
- **Multi-Language Support**: Bilingual AI responses supporting both English and Bengali (Bangla).
- **JWT-Based Authentication**: Role-based access control (`user` / `admin`) with secure access/refresh token rotation.
- **Immutable Prediction History**: User-scoped, append-only history with pagination, filtering, CSV export, and PDF clinical report generation.
- **System Administration & Monitoring**: User management, system health oversight, model registry inspection, and runtime diagnostics.

## Architecture

```
┌─────────────────────────────────────────┐               HTTPS/JSON               ┌────────────────────────────────────────────────────────┐
│           Frontend (React SPA)          │ ─────────────────────────────────────► │               Backend (FastAPI, /api/v1)               │
│  - Histopathology Analysis Dashboard    │                                        │  - Clean Layered Architecture (Routers/Services/Repos) │
│  - AI Knowledge Chat & Prediction Chat  │ ◄───────────────────────────────────── │  - Multi-Model Inference & Calibration Pipeline        │
│  - Markdown & Word-by-Word Streaming    │                                        │  - LLM Orchestration & RAG Retrieval Engine           │
└─────────────────────────────────────────┘                                        └───────────┬────────────────────────────────┬───────────┘
                                                                                               │                                │
                                                   ┌───────────────────────────────────────────┴───────────────┐                │
                                                   ▼                                                           ▼                ▼
                                         PostgreSQL (Neon)                                             AI Runtime Manager   Google Gemini API
                         ┌─────────────────────────────────────────────────┐                       (TensorFlow Instances,   (GenAI SDK: LLM &
                         │ • users & refresh_tokens                        │                         Hugging Face Hub)       Embeddings)
                         │ • prediction_history (with cached ai_summary)   │                                            
                         │ • chat_messages (conversational history)        │                                            
                         │ • knowledge_embeddings (pgvector, 768-dim)      │                                            
                         └─────────────────────────────────────────────────┘                                            
```

See the [Backend README](./backend/README.md#architecture) for the full
layered architecture (routers → services → repositories, the isolated
ML subsystem, and the LLM/RAG engine) and the [Frontend README](./Frontend/README.md#project-structure)
for the frontend's component design.

## Tech stack

| Layer | Stack |
|---|---|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, shadcn/ui (Radix primitives), TanStack Query, Axios, React Router, React Hook Form + Zod, Framer Motion, Lucide Icons |
| Backend | Python 3.10, FastAPI, Pydantic v2, SQLAlchemy (async) + Alembic, PyJWT, TensorFlow/Keras 2.10, ReportLab, Google GenAI SDK (`google-genai`), `pgvector` |
| LLM & RAG | Google Gemini (`gemini-3.5-flash-lite`, fallback cascade to 3.x series), `gemini-embedding-2` (768 dimensions), PostgreSQL `pgvector` cosine similarity retrieval |
| Database | PostgreSQL with `pgvector` extension (Neon in production; `postgres:16-alpine` with pgvector locally) |
| Model storage | Hugging Face Hub (checksum-verified downloads, on-disk cache) |
| Infra | Docker / Docker Compose, Nginx (frontend static serving); deployed on Netlify (frontend), Render (backend), Neon (database) |

## Repository layout

```
OncoVision/
├── Frontend/            # React 19 + TypeScript SPA (Chat, Predictions, Reports) — see Frontend/README.md
├── backend/              # FastAPI + PostgreSQL + TensorFlow + Gemini API — see backend/README.md
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
# Edit backend/.env:
# - Set a secure JWT_SECRET_KEY
# - Add your GOOGLE_API_KEY from https://aistudio.google.com/apikey

# 2. Build and start everything (PostgreSQL + backend + frontend)
docker compose up --build

# 3. Run database migrations (first run only, in a second terminal)
docker compose exec backend python -m alembic upgrade head
```

> **Note:** The backend automatically applies migrations and checks knowledge base ingestion on startup, so the tables and embeddings will initialize seamlessly!

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
  logs persist in named volumes.
- **`frontend`** — built from `Frontend/Dockerfile` (Node build stage →
  static `dist/` served by `nginx:alpine`), exposed on host port `3000`.

To stop everything: `docker compose down` (add `-v` to also delete named volumes).

## Running each service manually

For day-to-day development with hot reload:

- **Backend**:
  ```bash
  cd backend
  python -m venv venv
  source venv/bin/activate    # Windows: venv\Scripts\activate
  pip install -r requirements.txt
  cp .env.example .env        # Set GOOGLE_API_KEY, DATABASE_URL, JWT_SECRET_KEY
  uvicorn app.main:app --reload --port 8000
  ```
  See the [Backend README](./backend/README.md#running-locally).

- **Frontend**:
  ```bash
  cd Frontend
  npm install
  npm run dev
  ```
  See the [Frontend README](./Frontend/README.md#getting-started).

## Environment variables

Each service owns its configuration:

- **Backend** (`backend/.env`):
  - Database & Auth: `DATABASE_URL`, `JWT_SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`.
  - Storage & ML: `MODEL_STORAGE_PATH`, `UPLOAD_PATH`, `REPORT_PATH`, `HF_TOKEN`.
  - **LLM & RAG Integration**:
    - `GOOGLE_API_KEY`: Google AI Studio API key (required for Gemini LLM and embeddings).
    - `LLM_MODEL`: Active generation model (`gemini-3.5-flash-lite`, with fallback cascade).
    - `LLM_EMBEDDING_MODEL`: Embedding model (`gemini-embedding-2`).
    - `LLM_MAX_TOKENS`: Generation token cap (default `512`).
    - `LLM_TEMPERATURE`: Sampling temperature (default `0.2`).
    - `RAG_TOP_K`: Number of context documents to retrieve (default `3`).
    - `RAG_SIMILARITY_THRESHOLD`: Minimum cosine similarity score (default `0.7`).
    - `CHAT_RATE_LIMIT_MAX_REQUESTS`: Rate limit per hour (default `20`).
- **Frontend** (`Frontend/.env`):
  - `VITE_API_URL`: Base API URL (e.g. `http://localhost:8000/api/v1`).

See [Backend README](./backend/README.md#environment-variables) for complete details.

## API documentation

Once the backend is running, interactive docs are available at:

- Swagger UI — `http://localhost:8000/docs`
- ReDoc — `http://localhost:8000/redoc`
- OpenAPI schema — `http://localhost:8000/openapi.json`
- LLM Diagnostic — `http://localhost:8000/api/v1/system/test-llm`

## Testing

```bash
cd backend
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest tests -v
```

See the [Backend README](./backend/README.md#testing) for test suite organization.

## Disclaimer

OncoVision AI is a research and decision-support project. Predictions and AI conversational responses are
AI-generated model outputs — labeled as such throughout the UI — and are never presented as a confirmed
clinical diagnosis. It is not certified as a medical device and must not be used for actual clinical decision-making.

