"""Prediction Request supporting metadata (ADR-019, Phase 4.6.2).

Defines the small, framework-independent value objects embedded inside a
`PredictionRequest` (see `app.ml.prediction.prediction_request`):

- `UserContext`: a plain projection of the authenticated user, independent
  of the SQLAlchemy `User` ORM model.
- `PredictionRequestOptions`: a plain projection of the per-request control
  flags, independent of the service-layer `PredictionOptions`
  (`app.services.prediction_context`).
- `PredictionConfiguration`: the finalized, engine-facing configuration for
  this request, derived from `PredictionRequestOptions` plus the RUNTIME
  stage's outcome (`RuntimeValidationResult`, `RuntimeMetadata`).

Per the project's layering rule, `app/ml` never imports from
`app/services`. Every `from_source()` classmethod below therefore accepts
`Any` and reads the object it is given structurally (duck typing) --
exactly the same pattern already used by
`app.services.prediction_context.PredictionOptions.from_request()` -- so
`PredictionRequestBuilder` can be handed real service-layer objects
(`User`, `PredictionOptions`) without this module ever importing their
classes.

This module performs no AI inference, no image preprocessing, and never
communicates with the AI Runtime Manager, Prediction Engine, or Adaptive
Ensemble Engine.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class UserContext(BaseModel):
    """Plain, serializable projection of the authenticated user (ADR-019).

    Intentionally independent of `app.models.user.User` so this module
    never imports the ORM layer -- only the handful of fields relevant to
    a prediction request are carried across.
    """

    model_config = ConfigDict(frozen=True)

    user_id: str = Field(description="Unique identifier of the requesting user.")
    user_email: str = Field(description="Email address of the requesting user.")
    user_role: str | None = Field(
        default=None, description="Role of the requesting user (e.g. 'admin', 'user')."
    )
    is_active: bool = Field(
        default=True, description="Whether the requesting user's account is currently active."
    )

    @classmethod
    def from_source(cls, user: Any) -> "UserContext":
        """Build a `UserContext` from any object exposing the same fields.

        Accepts `app.models.user.User` (or any duck-typed equivalent)
        without importing its module.

        Args:
            user: The authenticated user submitting the prediction request.
        """
        user_id = getattr(user, "id", None)
        role = getattr(user, "role", None)
        return cls(
            user_id=str(user_id) if user_id is not None else "",
            user_email=getattr(user, "email", ""),
            user_role=getattr(role, "value", role) if role is not None else None,
            is_active=bool(getattr(user, "is_active", True)),
        )


class PredictionRequestOptions(BaseModel):
    """Plain, serializable projection of the validated per-request control flags.

    Field-for-field mirror of `app.services.prediction_context.PredictionOptions`,
    owned by the ML layer so `PredictionRequestBuilder` stays independent
    from the service layer (see module docstring).
    """

    model_config = ConfigDict(frozen=True)

    confidence_threshold: float = Field(
        description="Minimum confidence required for a prediction to be treated as reliable."
    )
    include_individual_predictions: bool = Field(
        description="Whether the response should include the per-model prediction breakdown."
    )
    include_runtime_statistics: bool = Field(
        description="Whether the response should include AI Runtime health/statistics."
    )
    save_history: bool = Field(
        description="Whether this prediction should be persisted to prediction history (Phase 5)."
    )
    generate_report: bool = Field(
        description="Whether a downloadable prediction report should be generated (Phase 6)."
    )

    @classmethod
    def from_source(cls, options: Any) -> "PredictionRequestOptions":
        """Build a `PredictionRequestOptions` from any object exposing the same fields.

        Accepts `app.services.prediction_context.PredictionOptions` (or any
        duck-typed equivalent) without importing its module, reading it
        through `model_dump()` when available and falling back to plain
        attribute access otherwise.

        Args:
            options: The validated prediction control flags for this request.
        """
        if hasattr(options, "model_dump"):
            data = options.model_dump()
        else:
            data = {field: getattr(options, field) for field in cls.model_fields}
        return cls(**data)


class PredictionConfiguration(BaseModel):
    """Finalized, engine-facing configuration for a single prediction request (ADR-019).

    Combines the caller's `PredictionRequestOptions` with a point-in-time
    snapshot of the RUNTIME stage's outcome, so the Prediction Engine
    (Phase 4.6.3 onward) can consume a single, self-contained
    configuration object instead of re-deriving it from separate request
    and runtime objects.
    """

    model_config = ConfigDict(frozen=True)

    confidence_threshold: float = Field(
        description="Effective confidence threshold the Prediction Engine must apply for this request."
    )
    include_individual_predictions: bool = Field(
        description="Whether the response should include the per-model prediction breakdown."
    )
    include_runtime_statistics: bool = Field(
        description="Whether the response should include AI Runtime health/statistics."
    )
    manifest_version: str = Field(
        description="Model Manifest version in effect when this request was built (ADR-006)."
    )
    runtime_version: str = Field(
        description="Application/runtime version in effect when this request was built."
    )
    loaded_model_count: int = Field(
        description=(
            "Number of models confirmed READY at request-build time -- the "
            "upper bound on how many individual predictions the Prediction "
            "Engine may produce for this request."
        )
    )

    @classmethod
    def build(
        cls,
        options: PredictionRequestOptions,
        runtime_metadata: Any,
        runtime_validation: Any,
    ) -> "PredictionConfiguration":
        """Derive a `PredictionConfiguration` from validated request options and runtime state.

        `runtime_metadata` and `runtime_validation` are read structurally
        (duck typing) so this module never imports
        `app.services.runtime_metadata.RuntimeMetadata` or
        `app.services.runtime_validator.RuntimeValidationResult` directly.

        Args:
            options: The already-projected `PredictionRequestOptions` for this request.
            runtime_metadata: The RUNTIME stage's metadata snapshot.
            runtime_validation: The RUNTIME stage's validation outcome.
        """
        return cls(
            confidence_threshold=options.confidence_threshold,
            include_individual_predictions=options.include_individual_predictions,
            include_runtime_statistics=options.include_runtime_statistics,
            manifest_version=getattr(runtime_metadata, "manifest_version", "unknown"),
            runtime_version=getattr(runtime_metadata, "runtime_version", "unknown"),
            loaded_model_count=getattr(runtime_validation, "loaded_model_count", 0),
        )
