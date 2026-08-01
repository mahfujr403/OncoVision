"""Prediction Runtime Validation (Phase 4.5.2 - ADR-015).

`RuntimeValidator` is the single reusable place a prediction request
verifies that the AI Runtime is in a usable state before the pipeline is
allowed to proceed toward preprocessing, inference, or ensembling.

This module performs NO AI inference, NO image preprocessing, and never
touches the Prediction Engine or Adaptive Ensemble Engine -- it only reads
runtime metadata through the existing `RuntimeAdapter` (ADR-014) and
produces a `RuntimeValidationResult`.

`RuntimeValidator` never talks to `AIRuntimeManager` directly and never
mutates it; it depends exclusively on `RuntimeAdapter`, preserving the
decoupling established in Phase 4.5.1.

Future prediction phases reuse this same module without change:
    - Phase 4.5.4 (Prediction Service Integration) calls `validate_or_raise()`
      as the first gate of `PredictionService.predict()`.
    - Phase 4.6 (Prediction Engine Integration) and Phase 4.7 (Ensemble
      Integration) rely on the pipeline never having reached them unless
      validation already passed.
"""

from pydantic import BaseModel, ConfigDict, Field

from app.core.logging import get_logger
from app.services.prediction_exceptions import (
    NoLoadedModelsError,
    RuntimeNotInitializedError,
    RuntimeUnavailableError,
    RuntimeValidationFailedError,
)
from app.services.runtime_adapter import RuntimeAdapter, RuntimeAvailability, RuntimeHealthSummary

logger = get_logger(__name__)


class RuntimeValidationResult(BaseModel):
    """Reusable outcome of a single AI Runtime validation check.

    Carries no TensorFlow objects or other live runtime references -- only
    plain, serializable validation facts -- so it can be logged, returned
    in diagnostics, or attached to a `PredictionResult` (Phase 4.5.4)
    without leaking internal runtime state.
    """

    model_config = ConfigDict(frozen=True)

    is_valid: bool = Field(
        description="Whether prediction may proceed: runtime initialized and at least one model loaded."
    )
    runtime_initialized: bool = Field(
        description="Whether the AI Runtime Manager has completed its startup loading sequence."
    )
    runtime_healthy: bool = Field(
        description="Whether the runtime's qualitative availability is OPERATIONAL or DEGRADED."
    )
    loaded_model_count: int = Field(
        description="Number of models currently in the READY state."
    )
    failed_model_count: int = Field(
        description="Number of models currently in the FAILED state."
    )
    validation_message: str = Field(
        description="Human-readable summary of the validation outcome."
    )


class RuntimeValidator:
    """Validates AI Runtime readiness on behalf of the prediction pipeline (ADR-015).

    Depends only on `RuntimeAdapter` (ADR-014), never on `AIRuntimeManager`
    or `ModelRegistry` directly, and performs no model loading, inference,
    preprocessing, or ensemble logic of any kind.
    """

    def __init__(self, runtime_adapter: RuntimeAdapter) -> None:
        self._runtime_adapter = runtime_adapter

    async def validate(self) -> RuntimeValidationResult:
        """Run every runtime validation check and return the combined result.

        Never raises for a determinate runtime-state outcome (not
        initialized, unhealthy, zero loaded models); those are reported as
        `is_valid=False` on the returned result. Only an unexpected failure
        while reading runtime state (e.g. a `RuntimeAdapter` collaborator
        error) propagates, as `RuntimeValidationFailedError`.
        """
        logger.info("Runtime validation started.")

        try:
            health: RuntimeHealthSummary = await self._runtime_adapter.get_runtime_health()
        except Exception as exc:
            logger.error("Runtime validation could not be completed.", exc_info=True)
            raise RuntimeValidationFailedError() from exc

        runtime_initialized = health.is_initialized
        logger.info(
            "Runtime initialized: %s",
            "yes" if runtime_initialized else "no",
        )

        runtime_healthy = health.availability in (
            RuntimeAvailability.OPERATIONAL,
            RuntimeAvailability.DEGRADED,
        )
        logger.info(
            "Runtime health status: %s (%s)",
            health.availability.value,
            "healthy" if runtime_healthy else "unhealthy",
        )

        logger.info("Loaded model count: %d", health.loaded_model_count)
        logger.info("Failed model count: %d", health.failed_model_count)

        if not runtime_initialized:
            logger.warning("Runtime unavailable: initialization has not completed yet.")
        elif health.loaded_model_count == 0:
            logger.warning("Zero loaded models detected: prediction cannot proceed.")

        is_valid = (
            runtime_initialized and runtime_healthy and health.loaded_model_count > 0
        )
        validation_message = self._build_validation_message(
            is_valid=is_valid,
            runtime_initialized=runtime_initialized,
            runtime_healthy=runtime_healthy,
            loaded_model_count=health.loaded_model_count,
            failed_model_count=health.failed_model_count,
        )

        result = RuntimeValidationResult(
            is_valid=is_valid,
            runtime_initialized=runtime_initialized,
            runtime_healthy=runtime_healthy,
            loaded_model_count=health.loaded_model_count,
            failed_model_count=health.failed_model_count,
            validation_message=validation_message,
        )

        logger.info(
            "Runtime validation completed: is_valid=%s loaded=%d failed=%d",
            result.is_valid,
            result.loaded_model_count,
            result.failed_model_count,
        )
        return result

    async def validate_or_raise(self) -> RuntimeValidationResult:
        """Validate the runtime and raise a specific error if prediction may not proceed.

        Raises:
            RuntimeNotInitializedError: The runtime has not finished its
                startup loading sequence.
            NoLoadedModelsError: The runtime is initialized but zero models
                are currently in the READY state.
            RuntimeUnavailableError: The runtime is initialized and has at
                least one loaded model, yet its qualitative availability is
                still not healthy (defensive fallback; not reachable under
                the current `RuntimeAdapter.get_runtime_health()` rules,
                which tie DEGRADED/OPERATIONAL directly to a positive
                loaded-model count).
            RuntimeValidationFailedError: Runtime state could not be read
                at all.

        Returns:
            The passing `RuntimeValidationResult`, for callers that want the
            full detail alongside the proceed/stop decision.
        """
        result = await self.validate()

        if result.is_valid:
            return result

        if not result.runtime_initialized:
            raise RuntimeNotInitializedError()

        if result.loaded_model_count == 0:
            raise NoLoadedModelsError()

        raise RuntimeUnavailableError()

    def _build_validation_message(
        self,
        is_valid: bool,
        runtime_initialized: bool,
        runtime_healthy: bool,
        loaded_model_count: int,
        failed_model_count: int,
    ) -> str:
        """Build a human-readable summary of the validation outcome."""
        if not runtime_initialized:
            return "The AI runtime has not finished initializing yet."

        if loaded_model_count == 0:
            return "No AI models are currently loaded and ready to serve predictions."

        if not runtime_healthy:
            return "The AI runtime is initialized but is not currently in a healthy state."

        if failed_model_count > 0:
            return (
                f"Runtime is operational in degraded mode: {loaded_model_count} model(s) "
                f"loaded, {failed_model_count} model(s) failed."
            )

        return f"Runtime is fully operational with {loaded_model_count} model(s) loaded."
