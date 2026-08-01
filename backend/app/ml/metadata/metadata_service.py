"""Provides reusable, read-only metadata about the model registry.

This service performs no model loading or prediction; it only reports on
manifest and cache state, and is the pattern future services (e.g. the
Phase 3.2 Model Manager) should follow.
"""

from app.ml.cache.cache_manager import ModelCacheManager
from app.ml.registry.model_registry import ModelRegistry
from app.ml.schemas import ModelManifestEntry, ModelRegistryResponse, ModelSummary


class ModelMetadataService:
    """Provides counts and summaries derived from the model registry and cache."""

    def __init__(self, registry: ModelRegistry, cache_manager: ModelCacheManager) -> None:
        self._registry = registry
        self._cache_manager = cache_manager

    def get_model_count(self) -> int:
        """Return the total number of registered models."""
        return len(self._registry.get_all_models())

    def get_enabled_count(self) -> int:
        """Return the number of models enabled in the manifest."""
        return len(self._registry.get_enabled_models())

    def get_disabled_count(self) -> int:
        """Return the number of models disabled in the manifest."""
        return self.get_model_count() - self.get_enabled_count()

    def get_available_models(self) -> list[ModelManifestEntry]:
        """Return enabled models whose weight files are currently cached locally."""
        return [
            model for model in self._registry.get_enabled_models()
            if self._cache_manager.is_cached(model)
        ]

    def get_manifest_summary(self) -> ModelRegistryResponse:
        """Return a complete summary of the manifest, registry, and cache state."""
        all_models = sorted(self._registry.get_all_models(), key=lambda model: model.priority)
        summaries = [
            ModelSummary(
                id=model.id,
                display_name=model.display_name,
                version=model.version,
                framework=model.framework,
                format=model.format,
                priority=model.priority,
                ensemble_weight=model.ensemble_weight,
                input_size=model.input_size,
                num_classes=model.num_classes,
                class_labels=model.class_labels,
                enabled=model.enabled,
                is_cached=self._cache_manager.is_cached(model),
                description=model.description,
            )
            for model in all_models
        ]

        return ModelRegistryResponse(
            manifest_version=self._registry.manifest_version,
            total_models=len(all_models),
            enabled_models=self.get_enabled_count(),
            disabled_models=self.get_disabled_count(),
            available_models=len(self.get_available_models()),
            models=summaries,
        )
