"""Centralized Image Preprocessing outcome (ADR-018, Phase 4.6.1).

`PreprocessingResult` is the single reusable object returned by
`ImagePreprocessor.preprocess()`. It carries every diagnostic fact about
how an uploaded image was prepared for inference, plus the resulting
model-ready tensor, so downstream stages (starting with the Prediction
Engine, Phase 4.6.3 onward) never need to re-derive this information.

Only ever constructed after every preprocessing stage has succeeded; a
failure at any stage raises a dedicated
`app.ml.preprocessing.exceptions.PreprocessingError` subclass instead, so
`preprocessing_success` is always `True` on a returned instance. The
field is still modeled explicitly (rather than omitted) so this result
stays a complete, self-describing outcome record if a future phase
chooses to represent partial/soft failures instead of raising.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

MANIFEST_SOURCE: str = "model_manifest"
DEFAULT_SOURCE: str = "default_configuration"


class PreprocessingResult(BaseModel):
    """Reusable outcome of a single centralized image preprocessing run."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    original_width: int = Field(description="Uploaded image width before preprocessing, in pixels.")
    original_height: int = Field(
        description="Uploaded image height before preprocessing, in pixels."
    )
    processed_width: int = Field(description="Image width after preprocessing, in pixels.")
    processed_height: int = Field(description="Image height after preprocessing, in pixels.")
    image_format: str = Field(
        description="Detected source image format (e.g. 'JPEG', 'PNG', 'TIFF')."
    )
    preprocessing_time_ms: float = Field(
        description="Total time spent across every preprocessing stage, in milliseconds."
    )
    preprocessing_success: bool = Field(
        description="Whether preprocessing completed successfully for this image."
    )
    processed_tensor: Any = Field(
        description=(
            "Batched NumPy array of shape "
            "`(1, processed_width, processed_height, 3)`, with raw pixel "
            "values in `[0, 255]` (float32), matching what every current "
            "production model was trained on, ready for model inference. "
            "Typed `Any` rather than "
            "`numpy.ndarray` so this model remains usable wherever a plain "
            "Pydantic type is expected; exclude it explicitly "
            "(`model_dump(exclude={'processed_tensor'})`) when serializing "
            "for logging or API responses."
        )
    )
    input_size: int = Field(
        description="Square input dimension used for resizing, in pixels."
    )
    preprocessing_source: str = Field(
        description=(
            "Origin of the preprocessing input size: 'model_manifest' when "
            "sourced from a registered model's `input_size` (ADR-006), or "
            "'default_configuration' when no registry/enabled model was "
            "available and the centralized default was used instead."
        )
    )
