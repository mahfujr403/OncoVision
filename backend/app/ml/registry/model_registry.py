"""Centralized, in-memory model registry built from the validated manifest.

All future model-related services must read model metadata through this
registry rather than hardcoding it. Supporting a new model, or a new
framework/format entirely, requires only a new manifest entry.
"""

from app.ml.exceptions import ModelNotFoundError
from app.ml.registry.manifest_loader import validate_manifest_integrity
from app.ml.schemas import ModelManifest, ModelManifestEntry


class ModelRegistry:
    """Provides read-only, validated access to registered model metadata."""

    def __init__(self, manifest: ModelManifest) -> None:
        self._manifest = manifest
        self._models_by_id: dict[str, ModelManifestEntry] = {
            model.id: model for model in manifest.models
        }
        self._models_by_priority: dict[int, ModelManifestEntry] = {
            model.priority: model for model in manifest.models
        }

    @property
    def manifest_version(self) -> str:
        """Return the version identifier of the loaded manifest."""
        return self._manifest.manifest_version

    def get_all_models(self) -> list[ModelManifestEntry]:
        """Return every registered model, enabled or not."""
        return list(self._manifest.models)

    def get_enabled_models(self) -> list[ModelManifestEntry]:
        """Return only models marked as enabled in the manifest."""
        return [model for model in self._manifest.models if model.enabled]

    def get_enabled_models_ordered_by_priority(self) -> list[ModelManifestEntry]:
        """Return every enabled model, ascending by Model Manifest loading priority.

        Used by sequential multi-model execution (ADR-021) to resolve
        execution order (currently MobileNetV2 -> DenseNet121 ->
        EfficientNetV2B0 + ResNet50 Feature Fusion) directly from the
        manifest rather than a hardcoded model order.
        """
        return sorted(self.get_enabled_models(), key=lambda model: model.priority)

    def get_model_by_id(self, model_id: str) -> ModelManifestEntry:
        """Return a registered model by its unique ID.

        Raises:
            ModelNotFoundError: If no model with the given ID is registered.
        """
        model = self._models_by_id.get(model_id)
        if model is None:
            raise ModelNotFoundError(f"No registered model found with ID '{model_id}'.")
        return model

    def get_model_by_priority(self, priority: int) -> ModelManifestEntry:
        """Return a registered model by its loading priority.

        Raises:
            ModelNotFoundError: If no model with the given priority is registered.
        """
        model = self._models_by_priority.get(priority)
        if model is None:
            raise ModelNotFoundError(f"No registered model found with priority '{priority}'.")
        return model

    def validate_manifest(self) -> None:
        """Re-run cross-entry integrity validation against the loaded manifest.

        Raises:
            ModelManifestError: If the manifest violates an integrity rule.
        """
        validate_manifest_integrity(self._manifest)
