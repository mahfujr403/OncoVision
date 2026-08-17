# CLEANUP — PHASE 5 FOLLOW-UP (SIDEBAR ACCURACY & UPLOAD LIMIT ALIGNMENT)

## Project Context

OncoVision AI is an enterprise-oriented AI Medical SaaS platform. UNDER DEVELOPMENT — never describe it as production-ready or clinically validated.

## Current Progress

Phase 4 (real auth) and Phase 5 (real prediction submission/results) are both confirmed complete and correct via source inspection. This is a small, scoped cleanup pass on pre-existing Phase 3-era static content that Phase 5 exposed as now visibly inaccurate next to the real result data it renders — it is not a new development phase and should not grow beyond what's listed here.

## Current Gap (confirmed by direct source inspection)

1. **`src/features/prediction/constants.ts`** contains `WORKFLOW_STEPS`, used live by `PredictionWorkflowCard.tsx`, with two factually wrong claims about backend behavior:
   - Step 2 description: *"Six ensemble models run in parallel for independent classification."* — the backend actually runs a sequential multi-model pipeline (ADR-021, confirmed in `app/api/v1/predictions/router.py` docstrings: *"Prediction Engine executes available models sequentially"*), and the real manifest has 3 registered models (EfficientNetV2B0+ResNet50 fusion, DenseNet121, MobileNetV2), not six.
   - Step 4 description: *"A structured clinical report is produced and available for download."* — confirmed false: `generate_report` is accepted by the backend for contract stability only and is **not acted on** (`app/api/v1/predictions/schemas.py`: *"Not yet acted on"*). No report is ever produced today.
2. **`ENSEMBLE_MODELS`** in the same file is a hardcoded, fictional 6-model list (ResNet50, DenseNet121, EfficientNetB4, MobileNetV3, VGG16, ViT-B16) that does not match the real manifest at all. Confirmed via `grep` that it is **not imported or rendered anywhere** — it's dead code.
3. **`IMAGE_REQUIREMENTS`** (same file, used live by `PredictionInfoCard.tsx`) states `"Maximum file size: 50 MB"`. The backend's actual limit, confirmed in `app/core/settings.py`, is `MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB`. A file between 10–50 MB will pass this UI's stated expectation and the frontend's own pre-validation, then get rejected by the backend with a 400 — misleading and inconsistent.
4. **`src/constants/app.ts`** — `MAX_IMAGE_SIZE_MB = 50` drives the frontend's own pre-upload validation (`usePredictionUpload.ts`'s `validateFile`), which is even more permissive than what the sidebar claims. This should be brought in line with the backend's real 10 MB limit so client-side validation actually catches oversized files before a wasted round-trip, per ADR-011's intent (frontend does UX pre-validation, backend remains authoritative — but the pre-validation should reflect the real limit to be useful).
5. **`src/features/auth/components/DemoCredentials.tsx`** still contains stale invented-role demo accounts (`researcher@oncovision.ai`, `doctor@oncovision.ai`, etc.) referencing the removed mock auth system. Confirmed unused/unimported anywhere in the app — dead code.
6. **`LoginPage.tsx`** and **`RegisterPage.tsx`** call `authService.login()` / `authService.register()` directly instead of the `useLogin()` / `useRegister()` TanStack Query mutation hooks already built in `useAuthQueries.ts` during Phase 4. Not a bug — both paths work — but it's an inconsistency with the rest of the app's data-fetching convention and means these two forms don't benefit from TanStack Query's built-in `isPending`/error state (they use local `isSubmitting`/`serverError` state instead, which still works correctly).

## Objective

Fix items 1–4 (factual accuracy / real-limit alignment) as required cleanup. Optionally fix items 5–6 if convenient, since they are low-risk dead-code/consistency items, not urgent, and should not be allowed to expand scope.

## Important Rules

- Do not touch the real, working `POST /api/v1/predictions` integration, `PredictionResultCard`/`IndividualModelsCard`/`RuntimeStatsCard`, or any Phase 4 auth internals beyond what's explicitly listed above.
- Do not invent a new "correct" model list to replace `ENSEMBLE_MODELS` — since it's unused, the correct fix is to **delete it**, not repopulate it with guessed model names. If a real model list is ever needed in the UI, it must come from the backend's `GET /api/v1/system/models` endpoint (Phase 9 scope), never hardcoded.
- Do not change `WORKFLOW_STEPS`' overall structure/step count without checking whether other components depend on exactly 4 steps (`stepStatusFromWorkspace` in `PredictionWorkflowCard.tsx` maps `WorkspaceStatus` to step indices 0–4) — only correct the two inaccurate description strings identified above, keep the step count and IDs stable unless you've confirmed nothing else depends on them.
- When correcting the "Generate Report" step description, do not simply delete the step — either reword it to accurately reflect current reality (e.g. reframe as a planned/future capability, clearly not implied to work today) or remove the step only if you've confirmed `stepStatusFromWorkspace`'s hardcoded step-to-status mapping is updated to match a 3-step flow. Prefer the reword-in-place option as lower-risk.
- Confirm the actual current value of `Settings.MAX_UPLOAD_SIZE` by re-inspecting `app/core/settings.py` before hardcoding `10` anywhere in the frontend — reflect whatever the backend's real current value is, not a value copied from this prompt without verification, in case it has changed since this review.
- If updating item 6, do not change the visual behavior/UX of `LoginPage`/`RegisterPage` — this must be a pure internal refactor (swap `authService` calls for the equivalent mutation hooks) with identical rendered behavior, loading states, and error messages.

## Required Implementation

1. In `src/features/prediction/constants.ts`:
   - Delete the unused `ENSEMBLE_MODELS` export entirely.
   - Correct `WORKFLOW_STEPS` step 2's description to accurately describe sequential multi-model inference (do not hardcode a model count in the copy — say something like "each available model runs inference in turn" rather than naming a specific number, since the number of active models is a backend/manifest concern that can change).
   - Correct `WORKFLOW_STEPS` step 4's description so it does not claim a report is produced today — reword to reflect that report generation is not yet available, or remove/relabel the step per the "Important Rules" guidance above.
   - Correct `IMAGE_REQUIREMENTS`'s `"Maximum file size"` value to match the backend's real, currently-confirmed `MAX_UPLOAD_SIZE`.
2. In `src/constants/app.ts`: update `MAX_IMAGE_SIZE_MB` to match the same real, currently-confirmed backend value, so `usePredictionUpload.ts`'s client-side `validateFile` pre-check is actually useful (catches oversized files before upload rather than after a wasted request).
3. *(Optional, only if convenient)* Delete `src/features/auth/components/DemoCredentials.tsx` since it is unused and references a removed mock system.
4. *(Optional, only if convenient)* Refactor `LoginPage.tsx`/`RegisterPage.tsx` to call `useLogin()`/`useRegister()` from `useAuthQueries.ts` instead of `authService` directly, preserving identical UX/error behavior.

## Files / Architecture