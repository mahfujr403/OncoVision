# OncoVision AI --- Frontend Development Guide

## 1. Purpose

This document is the authoritative frontend implementation guide for the
current OncoVision AI project.

OncoVision AI is an AI medical SaaS platform for Lung and Colon Cancer
Histopathology image classification using multiple deep learning models
and ensemble inference.

The frontend must be developed against the **actual current FastAPI
backend contract**.

### Core rule

The backend is authoritative for:

-   Authentication
-   Authorization
-   JWT/session validation
-   Prediction/inference
-   Ensemble logic
-   Confidence
-   Model execution
-   Prediction history
-   Analytics
-   Report generation
-   Runtime health
-   Model lifecycle
-   Administrative security

The frontend is responsible for:

-   User experience
-   Forms
-   Upload UX
-   Routing
-   Presentation
-   Tables
-   Charts
-   Filters
-   Pagination controls
-   Loading/error states
-   Accessibility
-   Responsive design
-   Animations

Do not duplicate backend business logic in the frontend.

------------------------------------------------------------------------

# 2. Current Technology Stack

Use the existing stack only:

-   React 19
-   TypeScript
-   Vite
-   Tailwind CSS
-   shadcn/ui
-   Framer Motion
-   TanStack Query
-   React Router
-   Axios
-   React Hook Form
-   Zod
-   Lucide React
-   Sonner
-   React Dropzone

Do not introduce additional state-management libraries unless a future
requirement genuinely requires one.

------------------------------------------------------------------------

# 3. Existing Frontend Architecture

Preserve the current feature-based architecture.

``` text
src/
├── app/
│   ├── App.tsx
│   ├── providers/
│   ├── router/
│   └── routes/
│
├── api/
│   ├── axios.ts
│   ├── interceptors.ts
│   ├── error-handler.ts
│   └── query-client.ts
│
├── components/
│   ├── ui/
│   ├── layout/
│   ├── feedback/
│   └── data-display/
│
├── features/
│   ├── auth/
│   ├── prediction/
│   ├── history/
│   ├── reports/
│   ├── profile/
│   ├── settings/
│   ├── admin/
│   ├── monitoring/
│   └── system/
│
├── layouts/
│   ├── LandingLayout.tsx
│   ├── AuthLayout.tsx
│   └── DashboardLayout.tsx
│
├── pages/
├── contexts/
├── hooks/
├── services/
├── types/
├── constants/
├── utils/
├── config/
├── routes/
├── providers/
├── lib/
├── assets/
└── styles/
```

Do not rewrite this architecture.

------------------------------------------------------------------------

# 4. Backend API Base URL

The frontend must use environment configuration.

Development:

``` env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

Production:

``` env
VITE_API_BASE_URL=https://your-backend-domain/api/v1
```

Never hardcode backend URLs inside feature components.

Never expose backend secrets in Vite environment variables.

------------------------------------------------------------------------

# 5. Backend API Map

The current backend API domains are:

``` text
/api/v1/health

/api/v1/system
/api/v1/system/models
/api/v1/system/runtime
/api/v1/system/models/status

/api/v1/auth
/api/v1/auth/register
/api/v1/auth/login
/api/v1/auth/refresh
/api/v1/auth/logout
/api/v1/auth/logout-all
/api/v1/auth/me

/api/v1/predictions
/api/v1/predictions/history
/api/v1/predictions/history/{history_id}

/api/v1/reports
/api/v1/reports/analytics
/api/v1/reports/export/csv
/api/v1/reports/export/pdf

/api/v1/admin/users
/api/v1/admin/users/{user_id}
/api/v1/admin/users/{user_id}/activate
/api/v1/admin/users/{user_id}/deactivate

/api/v1/admin/history
/api/v1/admin/history/{history_id}

/api/v1/admin/system

/api/v1/monitoring
```

The frontend must be implemented around these actual endpoints.

------------------------------------------------------------------------

# 6. API Architecture

Create one Axios instance:

``` text
src/api/axios.ts
```

Responsibilities:

-   Base URL
-   JSON defaults
-   Authorization header
-   Request configuration
-   Response handling
-   Authentication errors

Create:

``` text
src/api/interceptors.ts
src/api/error-handler.ts
```

Keep API logic outside React components.

------------------------------------------------------------------------

# 7. API Response Type

Use a shared API envelope where applicable:

``` ts
export interface ApiResponse<T> {
  success: boolean;
  message: string;
  data: T | null;
  errors?: unknown;
}
```

Do not manually parse response envelopes in every component.

------------------------------------------------------------------------

# 8. Authentication

The current backend provides real authentication.

The previous mock authentication implementation must eventually be
replaced by real backend integration.

## Authentication endpoints

``` text
POST /auth/register
POST /auth/login
POST /auth/refresh
POST /auth/logout
POST /auth/logout-all
GET  /auth/me
```

Authentication service:

``` text
features/auth/services/authService.ts
```

Methods:

``` ts
register()
login()
refresh()
logout()
logoutAll()
getMe()
```

Do not connect nonexistent endpoints such as forgot-password or
email-verification unless they are added to the backend.

------------------------------------------------------------------------

# 9. Authentication Session

Frontend session state should contain:

``` ts
interface AuthSession {
  user: User;
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
}
```

The exact token-storage strategy should follow the backend security
requirements.

Never store backend secrets in the frontend.

------------------------------------------------------------------------

# 10. User Type

The current backend user contract includes:

``` text
id
full_name
email
role
is_active
is_verified
avatar_url
last_login
created_at
```

Recommended frontend type:

``` ts
type UserRole = "USER" | "ADMIN";

interface User {
  id: string;
  full_name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
  avatar_url: string | null;
  last_login: string | null;
  created_at: string;
}
```

### Important

Do not assume the frontend supports a `RESEARCHER` role unless the
backend actually exposes and authorizes that role.

Backend authorization is authoritative.

------------------------------------------------------------------------

# 11. Token Refresh

Axios must implement automatic refresh.

Flow:

``` text
Request
   ↓
Attach Access Token
   ↓
Backend
   ↓
401?
 ┌─┴───────────┐
No             Yes
│               │
Return       Refresh Token
                │
          ┌─────┴─────┐
        Success      Failure
           │             │
      Retry Request    Logout
```

Important requirements:

-   Prevent infinite refresh loops.
-   Prevent multiple simultaneous refresh requests.
-   Queue requests while refresh is running.
-   Clear the session when refresh fails.
-   Redirect the user to login gracefully.

------------------------------------------------------------------------

# 12. Route Protection

Implement:

``` text
PublicRoute
ProtectedRoute
AdminRoute
```

Access model:

``` text
Guest
  ↓
Public pages

Authenticated USER
  ↓
Dashboard
Prediction
History
Reports
Profile
Settings

ADMIN
  ↓
All user features
Admin Users
Admin History
Admin System
Monitoring
```

Do not implement frontend-only authorization rules that the backend does
not recognize.

------------------------------------------------------------------------

# 13. Prediction API

The main prediction endpoint is:

``` text
POST /predictions
```

Request:

``` text
multipart/form-data
```

Required:

``` text
file
```

Optional parameters:

``` text
confidence_threshold
include_individual_predictions
include_runtime_statistics
save_history
generate_report
```

Example:

``` ts
const formData = new FormData();

formData.append("file", file);
formData.append("confidence_threshold", "0.5");
formData.append("include_individual_predictions", "true");
formData.append("include_runtime_statistics", "true");
formData.append("save_history", "true");
formData.append("generate_report", "false");
```

Do not manually set the multipart content type when Axios/browser
handles the FormData boundary.

------------------------------------------------------------------------

# 14. Prediction Feature

Recommended structure:

``` text
features/prediction/
├── api/
│   └── predictionApi.ts
├── components/
│   ├── UploadZone.tsx
│   ├── UploadCard.tsx
│   ├── ImagePreviewCard.tsx
│   ├── PredictionSettingsCard.tsx
│   ├── AnalyzeButton.tsx
│   ├── UploadProgress.tsx
│   ├── PredictionSummary.tsx
│   ├── ModelPredictionTable.tsx
│   ├── RuntimeStatistics.tsx
│   └── PredictionMetadata.tsx
├── hooks/
│   ├── usePrediction.ts
│   └── usePredictionUpload.ts
├── schemas/
│   └── predictionSchema.ts
├── services/
│   └── predictionService.ts
├── types/
│   └── prediction.types.ts
└── pages/
    ├── PredictionPage.tsx
    └── PredictionResultPage.tsx
```

------------------------------------------------------------------------

# 15. Prediction Settings

Frontend controls must map directly to backend request parameters.

  Frontend                   Backend
  -------------------------- ----------------------------------
  Confidence Threshold       `confidence_threshold`
  Individual Model Results   `include_individual_predictions`
  Runtime Statistics         `include_runtime_statistics`
  Save History               `save_history`
  Generate Report            `generate_report`

Do not create fake frontend-only model-selection controls unless the
backend exposes a corresponding API parameter.

------------------------------------------------------------------------

# 16. Prediction Response

The backend prediction response contains concepts including:

``` text
result
individual_predictions
runtime_statistics
metadata
```

The result includes:

``` text
prediction
confidence
agreement_ratio
successful_models
failed_models
participating_models
```

The frontend must only display these values.

Never calculate prediction, confidence, ensemble agreement, or model
success in React.

------------------------------------------------------------------------

# 17. Prediction Result UI

Recommended layout:

``` text
Prediction Complete
────────────────────────────────────

Image              Prediction Summary

                   Predicted Class
                   Confidence
                   Agreement Ratio
                   Successful Models
                   Failed Models

────────────────────────────────────
Individual Model Predictions

────────────────────────────────────
Runtime Statistics

────────────────────────────────────
Prediction Metadata
```

This should be one of the strongest pages in the application.

------------------------------------------------------------------------

# 18. Upload Validation

Frontend should validate:

``` text
JPG
JPEG
PNG
TIFF
```

and file size.

Frontend validation exists for UX.

Backend validation remains authoritative.

If the backend rejects the file, show a friendly server error.

Never assume frontend validation guarantees backend acceptance.

------------------------------------------------------------------------

# 19. History API

Main endpoint:

``` text
GET /predictions/history
```

Frontend should support backend-supported filters such as:

``` text
page
page_size
status
predicted_class
start_date
end_date
min_confidence
max_confidence
```

History UI:

``` text
Filter Toolbar
      ↓
History Table
      ↓
Pagination
```

------------------------------------------------------------------------

# 20. History Detail

Endpoint:

``` text
GET /predictions/history/{history_id}
```

Frontend route:

``` text
/history/:historyId
```

Display:

``` text
History ID
Request ID
Status
Image Filename
Prediction
Confidence
Agreement Ratio
Successful Models
Failed Models
Participating Models
Image Content Type
Image Size
Image Dimensions
Model Manifest Version
Processing Time
Created At
```

History records should be treated as immutable.

Do not implement frontend editing of prediction history.

------------------------------------------------------------------------

# 21. Reports

Backend endpoints:

``` text
GET /reports/analytics
GET /reports/export/csv
GET /reports/export/pdf
```

Reports page should contain:

``` text
Total Predictions
Successful Predictions
Failed Predictions
Success Rate
Average Confidence
Average Agreement Ratio
Class Distribution
Confidence Distribution
```

Only display metrics that the backend actually provides.

Do not invent medical or ML evaluation metrics.

For example, do not show accuracy, precision, recall, F1, or ROC unless
the backend supplies them.

------------------------------------------------------------------------

# 22. CSV Export

Endpoint:

``` text
GET /reports/export/csv
```

Frontend:

``` text
Export CSV
```

The browser should download the backend response.

Suggested filename:

``` text
prediction_history.csv
```

------------------------------------------------------------------------

# 23. PDF Export

Endpoint:

``` text
GET /reports/export/pdf
```

Frontend:

``` text
Download PDF Report
```

Suggested filename:

``` text
prediction_report.pdf
```

The frontend should not generate a fake medical report when the backend
already provides PDF generation.

------------------------------------------------------------------------

# 24. Admin User Management

Endpoints:

``` text
GET  /admin/users
GET  /admin/users/{user_id}
POST /admin/users/{user_id}/activate
POST /admin/users/{user_id}/deactivate
```

Admin users page:

``` text
Search
Pagination
User Table
User Details
Role
Active Status
Verified Status
Last Login
Created At
```

Actions:

``` text
Activate
Deactivate
```

Always treat backend errors as authoritative.

The backend prevents dangerous operations such as deactivating the
current administrator or removing the last active administrator.

------------------------------------------------------------------------

# 25. Admin History

Endpoints:

``` text
GET /admin/history
GET /admin/history/{history_id}
```

Admin history should include user information where provided.

Recommended columns:

``` text
User
Prediction
Confidence
Status
Models
Created At
```

Filters:

``` text
user_id
status
predicted_class
start_date
end_date
min_confidence
max_confidence
```

------------------------------------------------------------------------

# 26. System APIs

The backend exposes:

``` text
GET /system
GET /system/models
GET /system/runtime
GET /system/models/status
```

These should power the System Health / Model Runtime area.

------------------------------------------------------------------------

# 27. Model Registry UI

Endpoint:

``` text
GET /system/models
```

Display:

``` text
Model Name
Enabled
Manifest Version
Cache Availability
```

Do not allow the frontend to load, unload, download, or modify models
unless the backend later provides explicit mutation endpoints.

------------------------------------------------------------------------

# 28. Runtime UI

Endpoint:

``` text
GET /system/runtime
```

Display:

``` text
Runtime Status
Startup Time
Loaded Models
Failed Models
Pending Models
Memory Status
```

Use reusable status cards.

------------------------------------------------------------------------

# 29. Model Runtime Status

Endpoint:

``` text
GET /system/models/status
```

Possible model states include:

``` text
registered
downloading
downloaded
loading
ready
failed
disabled
```

Create a reusable:

``` text
ModelStatusBadge
```

component.

------------------------------------------------------------------------

# 30. Monitoring

Endpoint:

``` text
GET /monitoring
```

This should be restricted to administrators.

Possible monitoring sections:

``` text
Application Health
Database Connectivity
AI Runtime Health
Model Availability
HTTP Request Metrics
Prediction Request Metrics
```

Never expose secrets, environment variables, database credentials, or
private configuration.

------------------------------------------------------------------------

# 31. Admin System

Endpoint:

``` text
GET /admin/system
```

Recommended UI:

``` text
Application
Database
AI Runtime
Models
```

Use cards with clear health states.

------------------------------------------------------------------------

# 32. Health Check

Endpoint:

``` text
GET /health
```

Use it for lightweight backend availability indication.

Possible frontend states:

``` text
API Connected
API Unavailable
```

Avoid aggressive polling.

------------------------------------------------------------------------

# 33. TanStack Query

Use queries for server state.

Recommended query hooks:

``` text
useCurrentUser()
usePredictionHistory()
usePredictionHistoryDetail()
useAnalytics()
useAdminUsers()
useAdminUser()
useAdminHistory()
useAdminHistoryDetail()
useSystemInfo()
useModelRegistry()
useRuntimeHealth()
useModelStatuses()
useMonitoring()
useAdminSystem()
```

Use mutations for:

``` text
useLogin()
useRegister()
useLogout()
useLogoutAll()
useRefreshSession()
usePrediction()
useActivateUser()
useDeactivateUser()
```

------------------------------------------------------------------------

# 34. Query Keys

Centralize query keys:

``` ts
queryKeys.auth.me

queryKeys.history.list(filters)
queryKeys.history.detail(id)

queryKeys.reports.analytics

queryKeys.admin.users.list(params)
queryKeys.admin.users.detail(id)

queryKeys.admin.history.list(params)
queryKeys.admin.history.detail(id)

queryKeys.system.info
queryKeys.system.models
queryKeys.system.runtime
queryKeys.system.modelStatus

queryKeys.monitoring
```

This makes invalidation predictable.

------------------------------------------------------------------------

# 35. Cache Invalidation

After successful prediction:

``` text
Prediction mutation
      ↓
Invalidate prediction history
      ↓
Invalidate analytics
```

After activating/deactivating a user:

``` text
Invalidate admin users list
Invalidate user detail
```

Do not manually synchronize server state in multiple components.

------------------------------------------------------------------------

# 36. Error Handling

Normalize backend errors into a reusable frontend structure.

Handle at least:

``` text
400 Bad Request
401 Unauthorized
403 Forbidden
404 Not Found
409 Conflict
413 Payload Too Large
500 Internal Server Error
```

Recommended messages:

``` text
401
Your session has expired. Please sign in again.

403
You do not have permission to access this resource.

404
The requested record could not be found.

409
This action conflicts with the current system state.

413
The uploaded file is too large.

500
Something went wrong on the server.
```

Never expose raw backend stack traces to users.

------------------------------------------------------------------------

# 37. Dashboard

Dashboard should be driven by real backend data.

Recommended layout:

``` text
Welcome Header

Prediction Statistics
├── Total Predictions
├── Successful Predictions
├── Failed Predictions
└── Success Rate

Prediction Trends

Class Distribution

Confidence Distribution

Recent Predictions

API/System Status
```

Use:

``` text
/reports/analytics
/predictions/history
/health
```

as appropriate.

------------------------------------------------------------------------

# 38. Recommended Routes

``` text
/
├── /login
├── /register
│
└── /app
    ├── /dashboard
    ├── /predict
    ├── /prediction/:predictionId
    ├── /history
    ├── /history/:historyId
    ├── /reports
    ├── /profile
    ├── /settings
    │
    └── /admin
        ├── /users
        ├── /users/:userId
        ├── /history
        ├── /history/:historyId
        ├── /system
        └── /monitoring
```

------------------------------------------------------------------------

# 39. Features Not Yet Supported by the Current Backend

The original frontend plan mentioned:

``` text
Comparison
Benchmark
Saved Cases
Favorites
Notifications
Researcher role
Model Management mutations
Forgot Password
Reset Password
Email Verification
```

Do not pretend these are backend-integrated features unless
corresponding backend endpoints are added.

They can remain future-ready UI routes or be hidden until implemented.

------------------------------------------------------------------------

# 40. Frontend/Backend Responsibility Matrix

  Responsibility              Frontend   Backend
  ------------------------- ---------- ---------
  Form UX                          Yes 
  File picker                      Yes 
  Image preview                    Yes 
  Client validation                Yes 
  Server validation                          Yes
  JWT generation                             Yes
  JWT validation                             Yes
  Login UI                         Yes 
  Login processing                           Yes
  Token refresh request            Yes       Yes
  Prediction request               Yes 
  AI preprocessing                           Yes
  AI inference                               Yes
  Ensemble logic                             Yes
  Confidence                                 Yes
  History persistence                        Yes
  History display                  Yes 
  Analytics calculation                      Yes
  Analytics visualization          Yes 
  PDF generation                             Yes
  CSV generation                             Yes
  Model lifecycle                            Yes
  Monitoring                                 Yes
  Responsive UI                    Yes 
  Accessibility                    Yes 

------------------------------------------------------------------------

# 41. Security Rules

Never put these in the frontend:

``` text
JWT secret
Database credentials
Hugging Face tokens
Model credentials
Private API keys
Server environment variables
```

Frontend configuration should contain only public values such as:

``` env
VITE_API_BASE_URL=...
```

Do not rely on frontend route protection as the security boundary.

The backend must always enforce authorization.

------------------------------------------------------------------------

# 42. Performance Requirements

Use:

-   Route-level lazy loading
-   React Suspense
-   TanStack Query caching
-   Request deduplication
-   Pagination
-   Debounced search
-   Optimized image previews
-   Lazy chart rendering where appropriate
-   Avoid unnecessary global state
-   Avoid unnecessary re-renders
-   Memoize expensive UI only when profiling justifies it

Do not preload every admin page.

------------------------------------------------------------------------

# 43. Accessibility Requirements

All important interactive components must support:

-   Keyboard navigation
-   Visible focus
-   ARIA labels
-   Semantic HTML
-   Accessible dialogs
-   Accessible form errors
-   Screen-reader-friendly status messages
-   Keyboard-accessible drag/drop fallback
-   Proper button labels

Do not rely on color alone to communicate prediction or health status.

------------------------------------------------------------------------

# 44. Medical Product UX

OncoVision is a medical AI platform.

The UI must therefore avoid misleading claims.

Do not present:

``` text
Diagnosis confirmed
100% accurate
Cancer definitely detected
AI replaces physician
```

Use terminology such as:

``` text
AI Prediction
Predicted Class
Model Confidence
Model Agreement
AI-assisted analysis
```

The frontend should make clear that the displayed output is an AI model
prediction.

------------------------------------------------------------------------

# 45. Enterprise UI Principles

The interface should feel like a serious SaaS product.

Use:

-   Consistent spacing
-   Strong typography hierarchy
-   Clear information density
-   Professional tables
-   Meaningful empty states
-   Skeleton loading
-   Error boundaries
-   Confirmation dialogs
-   Toast notifications
-   Responsive navigation
-   Keyboard accessibility
-   Dark/light theme
-   Subtle Framer Motion animations

Avoid:

-   Excessive gradients
-   Fake statistics
-   Decorative dashboards without data
-   Placeholder cards presented as real functionality
-   Excessive animation
-   Generic template appearance

------------------------------------------------------------------------

# 46. Implementation Order

Build the backend integration in this order.

## Step 1 --- API Foundation

``` text
Axios
Environment config
API response types
Error normalization
Interceptors
Query client
```

## Step 2 --- Authentication

``` text
Register
Login
/me
Refresh
Logout
Logout all
Protected routes
Admin routes
```

## Step 3 --- Prediction

``` text
Upload
Validation
Prediction settings
POST /predictions
Loading state
Result page
Individual model results
Runtime statistics
Metadata
```

## Step 4 --- History

``` text
History list
Filters
Pagination
History detail
```

## Step 5 --- Reports

``` text
Analytics
Charts
CSV export
PDF export
```

## Step 6 --- Admin

``` text
Users
User details
Activate
Deactivate
Admin history
Admin history detail
```

## Step 7 --- System

``` text
System info
Model registry
Runtime
Model status
Admin system
Monitoring
```

## Step 8 --- Final Polish

``` text
Accessibility
Error states
Skeletons
Empty states
Responsive behavior
Performance
Security
Animations
```

------------------------------------------------------------------------

# 47. Definition of Done

The frontend integration is complete when:

-   [ ] Frontend uses the real FastAPI backend.
-   [ ] Mock authentication is removed.
-   [ ] Login works with backend.
-   [ ] Registration works with backend.
-   [ ] Session restoration works.
-   [ ] Token refresh works.
-   [ ] Logout works.
-   [ ] Logout-all works.
-   [ ] `/auth/me` populates the current user.
-   [ ] Protected routes work.
-   [ ] Admin routes are protected.
-   [ ] Prediction upload reaches `/predictions`.
-   [ ] Prediction response renders correctly.
-   [ ] Individual model results render correctly.
-   [ ] Runtime statistics render correctly.
-   [ ] Prediction metadata renders correctly.
-   [ ] History list works.
-   [ ] History filters work.
-   [ ] History pagination works.
-   [ ] History detail works.
-   [ ] Analytics works.
-   [ ] CSV export works.
-   [ ] PDF export works.
-   [ ] Admin user management works.
-   [ ] Admin history works.
-   [ ] System information works.
-   [ ] Model status works.
-   [ ] Monitoring works.
-   [ ] API errors are normalized.
-   [ ] Loading states are implemented.
-   [ ] Empty states are implemented.
-   [ ] Responsive behavior works.
-   [ ] Accessibility requirements are met.
-   [ ] No backend secrets exist in the frontend.
-   [ ] No fake ML results exist.
-   [ ] No unsupported backend functionality is presented as real
    functionality.

------------------------------------------------------------------------

# 48. Golden Rule for Future Frontend Development

For every new frontend feature, follow this sequence:

``` text
Backend endpoint
      ↓
Request schema
      ↓
Response schema
      ↓
Frontend TypeScript type
      ↓
API service
      ↓
TanStack Query hook
      ↓
Feature component
      ↓
Page
      ↓
Route
      ↓
Loading / Empty / Error states
      ↓
Accessibility
      ↓
Responsive polish
```

Never start with the UI and invent the API contract afterward.

The **current backend contract is the source of truth** for OncoVision's
frontend integration.
