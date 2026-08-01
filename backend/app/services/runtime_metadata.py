"""Prediction Runtime Metadata (Phase 4.5.3 - ADR-016).

`RuntimeMetadataService` is the single reusable place a prediction
request -- or any other caller, such as a future system/health endpoint
-- collects a point-in-time snapshot of AI Runtime metadata: which
models are loaded, which have failed, which are configured for lazy
loading, and which manifest, runtime, and framework versions are
currently in effect.

This module performs NO AI inference, NO image preprocessing, and never
touches the Prediction Engine or Adaptive Ensemble Engine -- it only
reads runtime and manifest metadata through the existing `RuntimeAdapter`
(ADR-014), exactly as `RuntimeValidator` does (Phase 4.5.2, ADR-015).

Per ADR-016, `RuntimeMetadataService` returns runtime metadata only. It
never receives or exposes internal `AIRuntimeManager` state: every value
on `RuntimeMetadata` is a plain, serializable Pydantic model or
primitive, and no TensorFlow object is ever constructed, referenced, or
returned by this module.

Future prediction phases reuse this same module without change:
    - Phase 4.5.4 (Prediction Service Integration) attaches a
      `RuntimeMetadata` snapshot to every `PredictionResult`.
    - Phase 8 (Monitoring) reuses this service for runtime/version
      reporting on system health endpoints.
"""

from pydantic import BaseModel, ConfigDict, Field

from app.core.logging import get_logger
from app.core.settings import Settings, get_settings
from app.ml.runtime.runtime_state import ModelRuntimeInfo
from app.services.prediction_exceptions import RuntimeMetadataCollectionFailedError
from app.services.runtime_adapter import RuntimeAdapter
from app.utils.environment import get_current_timestamp

logger = get_logger(__name__)


class RuntimeMetadata(BaseModel):
    """Point-in-time snapshot of AI Runtime and Model Manifest metadata.

    Carries no TensorFlow objects or other live runtime references --
    only plain, serializable metadata facts (ADR-016) -- so it can be
    logged, returned in diagnostics, or attached to a `PredictionResult`
    (Phase 4.5.4) without leaking internal `AIRuntimeManager` state.
    """

    model_config = ConfigDict(frozen=True)

    manifest_version: str = Field(
        description="Version identifier of the currently loaded Model Manifest (ADR-006)."
    )
    runtime_version: str = Field(
        description="Application/runtime version currently serving predictions."
    )
    frameworks: list[str] = Field(
        description="Distinct ML frameworks used by every registered model, sourced from the manifest."
    )
    startup_timestamp: str | None = Field(
        default=None,
        description="ISO 8601 timestamp the AI Runtime began its initialization sequence, or None if not yet started.",
    )
    loaded_models: list[ModelRuntimeInfo] = Field(
        description="Runtime metadata for every model currently in the READY state."
    )
    failed_models: list[ModelRuntimeInfo] = Field(
        description="Runtime metadata for every model currently in the FAILED state, with failure reasons."
    )
    lazy_models: list[ModelRuntimeInfo] = Field(
        description="Runtime metadata for every model registered with the LAZY loading strategy."
    )
    loaded_model_count: int = Field(description="Number of models currently in the READY state.")
    failed_model_count: int = Field(description="Number of models currently in the FAILED state.")
    lazy_model_count: int = Field(
        description="Number of models registered with the LAZY loading strategy."
    )
    collected_at: str = Field(
        description="ISO 8601 timestamp this metadata snapshot was collected."
    )


class RuntimeMetadataService:
    """Collects AI Runtime metadata on behalf of the prediction pipeline (ADR-016).

    Depends only on `RuntimeAdapter` (ADR-014), never on `AIRuntimeManager`
    or `ModelRegistry` directly, and performs no model loading, inference,
    preprocessing, or ensemble logic of any kind. No inference is
    triggered by any method on this class.
    """

    def __init__(
        self,
        runtime_adapter: RuntimeAdapter,
        settings: Settings | None = None,
    ) -> None:
        self._runtime_adapter = runtime_adapter
        self._settings = settings or get_settings()

    async def collect(self) -> RuntimeMetadata:
        """Assemble a complete `RuntimeMetadata` snapshot.

        Never raises for the normal absence of loaded, failed, or lazy
        models -- an empty runtime is a valid metadata snapshot. Only an
        unexpected failure while reading runtime or manifest state (e.g.
        a `RuntimeAdapter` collaborator error) propagates, as
        `RuntimeMetadataCollectionFailedError`.
        """
        logger.info("Runtime metadata collection started.")

        try:
            status = await self._runtime_adapter.get_runtime_status()
            loaded_models = await self._runtime_adapter.get_loaded_models()
            failed_models = await self._runtime_adapter.get_failed_models()
            lazy_models = await self._runtime_adapter.get_lazy_models()
            manifest_version = self._runtime_adapter.get_manifest_version()
            frameworks = self._runtime_adapter.get_frameworks()
        except Exception as exc:
            logger.error("Runtime metadata collection could not be completed.", exc_info=True)
            raise RuntimeMetadataCollectionFailedError() from exc

        metadata = RuntimeMetadata(
            manifest_version=manifest_version,
            runtime_version=self._settings.APP_VERSION,
            frameworks=frameworks,
            startup_timestamp=status.runtime_started_at,
            loaded_models=loaded_models,
            failed_models=failed_models,
            lazy_models=lazy_models,
            loaded_model_count=len(loaded_models),
            failed_model_count=len(failed_models),
            lazy_model_count=len(lazy_models),
            collected_at=get_current_timestamp(),
        )

        logger.info(
            "Runtime metadata collected: manifest_version=%s runtime_version=%s "
            "loaded=%d failed=%d lazy=%d",
            metadata.manifest_version,
            metadata.runtime_version,
            metadata.loaded_model_count,
            metadata.failed_model_count,
            metadata.lazy_model_count,
        )
        return metadata
