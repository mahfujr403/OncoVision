# OncoVision AI — Authoritative Project Context

> **Status:** UNDER DEVELOPMENT  
> **Last Updated:** 18 August 2026  
> **Purpose:** Authoritative context for future development, AI-assisted coding, frontend generation, documentation, and project decisions.

---

## 1. Project Overview

**OncoVision AI** is an enterprise-style AI medical imaging platform for **lung and colon cancer histopathology image classification**.

The project is being developed as a strong **AI/ML Engineer portfolio and showcase project**, demonstrating:

- Deep Learning
- Computer Vision
- Ensemble Learning
- FastAPI backend engineering
- Model serving
- Authentication
- Prediction history
- Reporting
- Admin capabilities
- Monitoring
- Docker/containerization
- Deployment optimization
- Modern React frontend architecture

### Important Status Rule

OncoVision AI is **UNDER DEVELOPMENT**.

It must **NOT** be described as:

- Production-ready
- Clinically validated
- A medical diagnostic system
- FDA/CE approved
- A replacement for pathologists/doctors
- Clinically deployable

The application should be presented as an **AI research/engineering platform and prototype**.

---

# 2. Current Source of Truth

The project has two major codebases:

### Backend

The current backend is the primary source of truth for frontend functionality.

Current backend package:

`oncovision-backend-phase9-deployment-optimization.zip`

### Existing Frontend

The previous frontend is:

`project 8.zip`

The existing frontend is primarily a **UI/reference starting point**.

For the new frontend direction:

> **Backend capabilities determine what the frontend is allowed to expose.**

The frontend must not invent backend functionality.

---

# 3. Frontend Development Direction

The frontend is being **rebuilt/refined against the current backend**, rather than forcing the backend to adapt to the old frontend.

The frontend should be designed as an **enterprise-level showcase application** suitable for an AI/ML Engineer portfolio.

### Frontend Design Principle

The UI should communicate:

> AI + Medical Imaging + Engineering + Reliability + Explainability + Professional Product Design

It should avoid looking like:

- A generic CRUD dashboard
- A basic student project
- A simple image classifier
- A fake hospital system
- A marketing-only landing page

---

# 4. Frontend Technology Stack

The intended frontend stack is:

- React 19
- TypeScript
- Vite
- Tailwind CSS
- shadcn/ui
- Framer Motion
- TanStack Query
- React Router
- Axios
- React Hook Form
- Zod

The architecture should remain modular and feature-oriented.

---

# 5. Frontend Architecture

The frontend uses a feature-based structure under:

```text
src/app/
```

The application provider hierarchy is:

```text
ThemeProvider
    ↓
QueryProvider
    ↓
AuthProvider
    ↓
RouterProvider
```

The frontend should maintain clear separation between:

- Authentication
- API communication
- Prediction
- History
- Reports
- Admin
- Monitoring
- Shared UI
- Application shell
- State/query management

---

# 6. Backend Technology

The backend is based on:

- FastAPI
- Python
- PostgreSQL
- SQLAlchemy / async database stack
- JWT authentication
- TensorFlow/Keras
- REST APIs
- Docker
- Hugging Face-hosted model artifacts

The backend exposes the actual application capabilities through REST APIs.

Frontend integration should be based on the real backend API contracts.

---

# 7. Authentication

Authentication is part of the platform.

Expected capabilities include:

- User registration
- User login
- JWT-based authentication
- Authenticated API requests
- Protected application routes
- User-specific prediction history

Frontend authentication should reflect the actual backend implementation.

Do not create frontend-only authentication logic that contradicts the backend.

---

# 8. Prediction System

OncoVision AI supports histopathology image prediction.

### Supported image formats

```text
JPG
JPEG
PNG
TIFF
```

The frontend should provide a professional prediction workflow:

1. Select/upload image
2. Validate file
3. Preview image
4. Submit prediction
5. Show processing state
6. Display prediction result
7. Display available model/ensemble information
8. Display confidence/probability information when provided by backend
9. Allow access to relevant history/report functionality

Do not display fabricated model metrics or explanations.

---

# 9. Model Architecture

The backend integrates multiple deep-learning models.

Known model components include:

### DenseNet121

Approximate model size:

```text
118 MB
```

### MobileNetV2

Approximate model size:

```text
109 MB
```

### InceptionV3

Approximate model size:

```text
191 MB
```

This model has poor relative accuracy and is not the preferred model.

### EfficientNetV2B0 + ResNet50 Fusion

Approximate model size:

```text
743 MB
```

### EfficientNetV2S + ResNet50 Fusion

Approximate model size:

```text
812 MB
```

Some large model artifacts are hosted through Hugging Face.

---

# 10. Model Loading Priority

The backend uses memory-aware model loading.

The intended priority is:

```text
1. MobileNetV2
        ↓
2. DenseNet121
        ↓
3. EfficientNetV2B0 + ResNet50 Fusion
```

If memory is insufficient for a model, the system should attempt the next appropriate model.

### Critical Rule

The API should not fail simply because one optional model cannot be loaded.

The system should degrade gracefully according to the backend's implemented model-loading strategy.

The frontend should reflect actual availability returned by the backend.

It must not assume every model is always available.

---

# 11. Ensemble Engine

The project includes ensemble/fusion capabilities.

Ensemble functionality must only be shown in the UI when supported by the backend API.

The frontend must not simulate ensemble predictions.

Any displayed:

- Ensemble result
- Model contribution
- Confidence
- Prediction score
- Model status

must come from backend data or clearly be identified as frontend-derived UI information.

---

# 12. Prediction History

Prediction history is implemented.

Current capabilities include:

- Saving prediction records
- Retrieving prediction history
- Pagination
- User-specific history
- Viewing individual prediction records

The frontend should provide a professional history interface.

Potential UI elements:

- Search/filter
- Pagination
- Prediction date
- Image/reference
- Predicted class
- Confidence
- Model/ensemble information
- Status
- Detail view

Only expose fields actually returned by the backend.

---

# 13. Reporting

Reporting APIs are part of the platform.

The frontend may provide:

- Prediction report view
- Report details
- Download/export actions where backend-supported
- Professional report presentation

Do not invent report-generation capabilities that are not implemented.

---

# 14. Admin

Admin functionality is part of the planned/current backend roadmap.

Admin UI should only expose backend-supported administrative operations.

Possible areas include:

- User management
- System statistics
- Model information
- Prediction monitoring
- System status

The exact UI must follow the backend API contract.

Never create fake admin actions.

---

# 15. Monitoring

Monitoring is part of the project roadmap.

The frontend may expose system health/status information when supported by backend APIs.

Possible concepts:

- API health
- Model availability
- System status
- Prediction activity
- Resource/model status

Do not present fabricated real-time metrics.

---

# 16. Deployment

Docker support is part of the project.

The backend has been containerized using Docker Compose.

The backend container exposes:

```text
8000
```

The API has a health endpoint under:

```text
/api/v1/health
```

The Docker environment uses PostgreSQL as the database service.

The database connection inside Docker follows the service hostname pattern:

```text
postgresql+asyncpg://postgres:postgres@db:5432/oncovision
```

Environment variables should remain configurable.

---

# 17. Docker Rules

When backend code changes:

- Determine whether the change affects the Docker image.
- Rebuild the image when dependencies, Dockerfile, or copied build content requires it.
- If only runtime-mounted/source content changes and the compose setup supports it, rebuilding may not always be necessary.

Do not unnecessarily modify Docker architecture.

---

# 18. API Integration Rules

The frontend must follow these principles:

### Rule 1 — Backend is authoritative

If the backend does not support a feature, the frontend should not pretend it does.

### Rule 2 — No fabricated data

Do not hardcode fake:

- Predictions
- Confidence values
- Model accuracy
- User statistics
- System metrics
- Reports
- Admin statistics

### Rule 3 — Graceful loading

Use proper:

- Loading states
- Empty states
- Error states
- Retry states
- Disabled states

### Rule 4 — API failures must be understandable

Display useful user-facing errors without exposing sensitive backend stack traces.

---

# 19. Medical UX Rules

Because this is a medical-imaging AI project, the UI must be responsible.

The frontend should clearly communicate that:

> Results are AI-generated research/engineering outputs and are not a clinical diagnosis.

Avoid language such as:

- "You have cancer"
- "Confirmed cancer"
- "Definitive diagnosis"
- "Guaranteed diagnosis"

Prefer:

- "AI Prediction"
- "Model Prediction"
- "Predicted Class"
- "Confidence Score"
- "Research Result"

---

# 20. UI/UX Design Direction

The visual language should feel:

- Enterprise
- Modern
- Scientific
- Trustworthy
- Technical
- Minimal
- Premium

Avoid excessive:

- Gradients
- Neon colors
- Glassmorphism
- Decorative animations
- Huge marketing text
- Fake statistics
- Generic AI imagery

Animations should be subtle and purposeful.

---

# 21. Important Frontend Screens

The frontend should be structured around the actual application capabilities.

Core areas may include:

### Public

- Landing page
- Product overview
- Technology/AI overview
- About/project information
- Login
- Registration

### Authenticated

- Dashboard
- Prediction workspace
- Prediction result
- Prediction history
- Prediction details
- Reports
- Profile/settings

### Administrative

- Admin dashboard
- User management
- System/model monitoring
- Administrative statistics

Exact screens must be aligned with backend capabilities.

---

# 22. Dashboard Philosophy

The dashboard should be useful rather than decorative.

It should prioritize information such as:

- Recent predictions
- Prediction activity
- Available model information
- System status
- Quick prediction action
- Recent history

Only real backend data should populate dynamic metrics.

---

# 23. Prediction Workspace Philosophy

The prediction workspace is one of the most important screens.

It should feel like a professional AI inference environment.

Recommended structure:

```text
Upload Area
    ↓
Image Preview
    ↓
Prediction Configuration
    ↓
Inference Progress
    ↓
Prediction Result
    ↓
Model / Confidence Information
    ↓
History / Report Actions
```

The UI should clearly distinguish:

- Input image
- AI prediction
- Confidence/probability
- Model information
- Disclaimer

---

# 24. History UX

History should support efficient exploration of previous predictions.

Recommended structure:

```text
History
├── Filters
├── Search
├── Prediction Table/List
├── Pagination
└── Prediction Detail
```

Use pagination according to backend support.

Do not load all records unnecessarily.

TanStack Query should be used appropriately for server-state management.

---

# 25. Error Handling

The frontend should handle:

- Invalid image format
- Oversized image
- Authentication failure
- Expired JWT
- Network failure
- API timeout
- Prediction failure
- Model unavailable
- Empty history
- Missing report
- Permission errors
- Server errors

Errors should be presented in human-readable language.

---

# 26. Performance Requirements

The frontend should be optimized for:

- Fast initial load
- Lazy loading
- Efficient API requests
- Query caching
- Image preview optimization
- Minimal unnecessary re-renders
- Code splitting where appropriate

Avoid adding unnecessary dependencies.

---

# 27. Security Rules

Never expose:

- JWT secrets
- Database credentials
- API private keys
- Hugging Face private tokens
- Backend secrets

Frontend environment variables must only contain values that are safe to expose to the client.

Authentication tokens must be handled according to the backend's security design.

---

# 28. Development Phases

The overall project roadmap is:

```text
Phase 1  — Foundation
Phase 2  — Authentication & Database
Phase 3  — Model Infrastructure
Phase 4  — Prediction Engine
Phase 5  — Ensemble Engine
Phase 6  — Prediction APIs
Phase 7  — Prediction History
Phase 8  — Reports
Phase 9  — Admin
Phase 10 — Monitoring
Phase 11 — Deployment Optimization
Phase 12 — Production Polish
```

Completed/current backend work has progressed through the later phases, including deployment optimization.

The exact current implementation should always be verified from the latest backend source code rather than relying only on this roadmap.

---

# 29. Current Frontend Strategy

The frontend should now be treated as a **backend-targeted rebuild/refinement**.

The old frontend should not dictate backend behavior.

Instead:

```text
Current Backend
      ↓
API Contract
      ↓
Frontend Data Model
      ↓
Feature Architecture
      ↓
UI/UX
```

This direction is mandatory for future frontend work.

---

# 30. Figma AI Development

The frontend UI is being designed/generated using **Figma AI**.

Figma prompts should therefore:

- Reference real OncoVision capabilities
- Avoid inventing unsupported features
- Define complete screen behavior
- Specify responsive layouts
- Include desktop/tablet/mobile considerations
- Maintain consistent design language
- Provide reusable components
- Clearly define loading/error/empty states
- Preserve accessibility
- Reflect the backend API capabilities

Figma-generated UI is a design starting point, not a source of truth for backend functionality.

---

# 31. AI-Assisted Coding Rules

When using Claude, ChatGPT, Cursor, or other coding assistants:

### Before modifying code

1. Inspect the existing implementation.
2. Identify the current architecture.
3. Verify API contracts.
4. Avoid unnecessary rewrites.
5. Preserve working functionality.

### When adding functionality

1. Check whether backend support exists.
2. Follow existing conventions.
3. Add proper error handling.
4. Add loading/empty states.
5. Keep TypeScript types accurate.
6. Avoid duplicated logic.

### Never

- Invent API endpoints
- Invent response fields
- Replace working architecture unnecessarily
- Hardcode backend data
- Claim unsupported functionality exists

---

# 32. Portfolio Positioning

OncoVision AI is intended to demonstrate the user's capability as an:

- AI/ML Engineer
- Machine Learning Engineer
- Computer Vision Engineer
- Applied AI Engineer
- Deep Learning Engineer
- AI Backend Engineer
- ML Software Engineer
- MLOps/ML Platform Engineer

The project should therefore demonstrate **engineering depth**, not only model accuracy.

Important showcase areas:

```text
Computer Vision
+
Deep Learning
+
Model Serving
+
Ensemble Learning
+
FastAPI
+
Database
+
Authentication
+
Prediction History
+
Reporting
+
Docker
+
Deployment Optimization
+
Modern Frontend
```

---

# 33. Documentation Rules

Documentation should clearly distinguish:

### Implemented

Features confirmed by the current code/backend.

### Planned

Features on the roadmap but not yet implemented.

### Frontend-derived

Pure UI/UX features that do not require backend support.

Never describe planned functionality as implemented.

---

# 34. Current Project Principle

The most important project principle is:

> **Build a credible, technically strong AI platform around the real backend—not a visually impressive frontend that claims capabilities the backend does not have.**

The frontend should make the backend's engineering capabilities easy to understand.

---

# 35. Source-of-Truth Priority

When information conflicts, use this priority:

```text
1. Current backend source code
2. Current API schemas/routes
3. Current database/model implementation
4. Current frontend implementation
5. This context document
6. Older project conversations
7. Old phase assumptions
```

Older information must not override the latest implementation.

---

# 36. Final Constraint

Every future OncoVision task should preserve these principles:

- Backend-first capability validation
- No fabricated functionality
- No fabricated metrics
- No clinical claims
- No unnecessary architecture rewrites
- Enterprise-level UX
- Portfolio-quality engineering
- Clean TypeScript
- Maintainable feature-based architecture
- Responsive UI
- Accessibility
- Strong error handling
- Real API integration
- Docker/deployment awareness
- Clear distinction between implemented and planned features

**OncoVision AI remains UNDER DEVELOPMENT.**