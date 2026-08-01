"""Stateless image transform primitives for centralized preprocessing (ADR-018).

Each function performs exactly one pipeline stage and raises a dedicated
`app.ml.preprocessing.exceptions.PreprocessingError` subclass on failure.
None of these functions perform I/O, validation, or AI inference; they
operate only on already-decoded, in-memory image data and are reused
as-is by `app.ml.preprocessing.image_preprocessor.ImagePreprocessor`.
"""

import numpy as np
from PIL import Image

from app.ml.preprocessing.exceptions import (
    ImageConversionError,
    ImageNormalizationError,
    ImageResizeError,
)

_RGB_MODE = "RGB"


def convert_to_rgb(image: Image.Image) -> Image.Image:
    """Convert `image` to RGB mode, regardless of its source color mode.

    Raises:
        ImageConversionError: If the conversion fails.
    """
    try:
        return image.convert(_RGB_MODE)
    except (OSError, ValueError) as exc:
        raise ImageConversionError() from exc


def resize_image(image: Image.Image, input_size: int) -> Image.Image:
    """Resize `image` to a square `(input_size, input_size)` using LANCZOS resampling.

    Args:
        image: An RGB-converted image.
        input_size: The target square dimension, sourced from the Model
            Manifest or centralized default configuration.

    Raises:
        ImageResizeError: If resizing fails.
    """
    try:
        return image.resize((input_size, input_size), Image.Resampling.LANCZOS)
    except (OSError, ValueError) as exc:
        raise ImageResizeError() from exc


def normalize_pixels(image: Image.Image) -> np.ndarray:
    """Convert `image` into a float32 NumPy array with raw `[0, 255]` pixel values.

    Every current production model (MobileNetV2, DenseNet121, and the
    EfficientNetV2B0 + ResNet50 fusion model) was trained and evaluated
    directly against `tf.keras.utils.image_dataset_from_directory` output.
    Its `Rescaling(1./255)` layer was defined in the training notebook but
    never wired into the training/evaluation pipeline, so every model
    learned on -- and expects -- raw `[0, 255]` float pixel values, not
    `[0, 1]`-normalized input. Rescaling here would silently feed every
    model out-of-distribution input at inference time, so this function
    intentionally performs a dtype conversion only, with no rescaling.

    Raises:
        ImageNormalizationError: If array conversion fails.
    """
    try:
        array = np.asarray(image, dtype=np.float32)
    except (TypeError, ValueError) as exc:
        raise ImageNormalizationError() from exc
    return array


def to_batch_tensor(array: np.ndarray) -> np.ndarray:
    """Expand a single `(H, W, C)` array into a batched `(1, H, W, C)` tensor.

    Raises:
        ImageNormalizationError: If the batch dimension cannot be added.
    """
    try:
        return np.expand_dims(array, axis=0)
    except (TypeError, ValueError) as exc:
        raise ImageNormalizationError() from exc
