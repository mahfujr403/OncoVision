"""Centralized Image Preprocessing pipeline (ADR-018, Phase 4.6.1).

`ImagePreprocessor` is the single reusable place a validated upload is
turned into a model-ready tensor. It runs strictly between centralized
upload validation (ADR-011) and the AI Runtime Manager in the prediction
pipeline (Project Context, Section 15):

    Image Upload -> Image Validation -> Image Preprocessing ->
    AI Runtime Manager -> Individual Model Prediction -> ...

This module performs NO AI inference. It never instantiates or calls
`AIRuntimeManager`, `PredictionEngine`, or `AdaptiveEnsembleEngine`. It
depends only on `ModelRegistry` -- a pure, static reader of the validated
Model Manifest -- so preprocessing settings are never hardcoded (ADR-006).

Pipeline stages performed here, in order:
    1. Read/decode the uploaded image (`PreprocessingReadabilityValidator`)
    2. Validate readability
    3. Convert to RGB (`transforms.convert_to_rgb`)
    4. Resize to the resolved input size (`transforms.resize_image`)
    5. Convert pixel values to float32, preserving the raw `[0, 255]`
       range every current production model was trained on
       (`transforms.normalize_pixels`)
    6. Convert to a NumPy array (`transforms.normalize_pixels`)
    7. Expand the batch dimension (`transforms.to_batch_tensor`)
    8. Generate preprocessing metadata (`PreprocessingResult`)

`PredictionService` (Phase 4.6.1 onward) delegates to this class before
any inference begins, and stops the pipeline immediately -- never
reaching the AI Runtime Manager -- if preprocessing fails.
"""

import time

from app.core.logging import get_logger
from app.core.settings import Settings, get_settings
from app.ml.preprocessing.exceptions import PreprocessingError
from app.ml.preprocessing.preprocessing_result import (
    DEFAULT_SOURCE,
    MANIFEST_SOURCE,
    PreprocessingResult,
)
from app.ml.preprocessing.transforms import (
    convert_to_rgb,
    normalize_pixels,
    resize_image,
    to_batch_tensor,
)
from app.ml.preprocessing.validators import PreprocessingReadabilityValidator
from app.ml.registry.model_registry import ModelRegistry

logger = get_logger(__name__)


class ImagePreprocessor:
    """Converts validated uploaded image bytes into a model-ready input tensor.

    Reusable across every current and future AI model (ADR-018): the
    input size driving resizing is resolved from the Model Manifest via
    `ModelRegistry` whenever a registry with at least one enabled model is
    available, and falls back to `Settings.DEFAULT_PREPROCESSING_INPUT_SIZE`
    otherwise. No preprocessing setting is ever hardcoded per model.
    """

    def __init__(
        self,
        registry: ModelRegistry | None = None,
        settings: Settings | None = None,
        validator: PreprocessingReadabilityValidator | None = None,
    ) -> None:
        self._registry = registry
        self._settings = settings or get_settings()
        self._validator = validator or PreprocessingReadabilityValidator()

    def preprocess(self, image_bytes: bytes) -> PreprocessingResult:
        """Run every preprocessing stage against a single uploaded image.

        Args:
            image_bytes: Raw uploaded image bytes, already accepted by
                `UploadValidator` (ADR-011).

        Returns:
            A `PreprocessingResult` describing the outcome, including the
            normalized, batched input tensor.

        Raises:
            UnreadableImageError: If the image cannot be decoded.
            ImageConversionError: If RGB conversion fails.
            ImageResizeError: If resizing fails.
            ImageNormalizationError: If normalization or tensor conversion fails.
        """
        started_at = time.perf_counter()
        logger.info("Preprocessing started.")

        try:
            image = self._validator.validate_readable(image_bytes)
            original_width, original_height = image.size
            image_format = image.format or "UNKNOWN"
            logger.info(
                "Image loaded: format=%s size=%dx%d",
                image_format,
                original_width,
                original_height,
            )

            input_size, preprocessing_source = self._resolve_input_size()

            rgb_image = convert_to_rgb(image)
            resized_image = resize_image(rgb_image, input_size)
            logger.info(
                "Image resized: %dx%d -> %dx%d",
                original_width,
                original_height,
                input_size,
                input_size,
            )

            normalized_array = normalize_pixels(resized_image)
            logger.info("Normalization completed.")

            processed_tensor = to_batch_tensor(normalized_array)
        except PreprocessingError:
            logger.warning("Preprocessing failed for the uploaded image.")
            raise

        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.info("Preprocessing completed in %.2f ms.", elapsed_ms)

        return PreprocessingResult(
            original_width=original_width,
            original_height=original_height,
            processed_width=input_size,
            processed_height=input_size,
            image_format=image_format,
            preprocessing_time_ms=elapsed_ms,
            preprocessing_success=True,
            processed_tensor=processed_tensor,
            input_size=input_size,
            preprocessing_source=preprocessing_source,
        )

    def _resolve_input_size(self) -> tuple[int, str]:
        """Resolve the square input size to preprocess for.

        Prefers the enabled model with the lowest (highest-priority)
        `priority` value registered in the Model Manifest. Falls back to
        `Settings.DEFAULT_PREPROCESSING_INPUT_SIZE` only when no registry
        was injected or the registry currently has zero enabled models.

        Returns:
            A `(input_size, source)` tuple, where `source` is one of
            `preprocessing_result.MANIFEST_SOURCE` or
            `preprocessing_result.DEFAULT_SOURCE`.
        """
        if self._registry is not None:
            enabled_models = self._registry.get_enabled_models()
            if enabled_models:
                primary_model = min(enabled_models, key=lambda model: model.priority)
                return primary_model.input_size, MANIFEST_SOURCE

        return self._settings.DEFAULT_PREPROCESSING_INPUT_SIZE, DEFAULT_SOURCE
