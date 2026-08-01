"""Readability validation for the centralized Image Preprocessing pipeline (ADR-018).

`PreprocessingReadabilityValidator` is a narrow, defensive check performed
immediately before preprocessing begins. It is intentionally distinct from
two other validation layers already in the pipeline:

- `app.core.upload.UploadValidator` (ADR-011): validates the raw upload
  itself -- existence, MIME type, extension, size, and basic image
  integrity -- before the request is accepted at all.
- `app.ml.prediction.validator.ImageValidator` (ADR-008): re-validates
  format and resolution inside the Prediction Engine, immediately before
  per-model inference.

Neither of those guarantees the image bytes are still safely decodable at
the moment preprocessing runs, so this validator performs one final,
minimal readability check and returns a fresh, usable `PIL.Image.Image`.
It performs no resizing, normalization, or inference of any kind.
"""

from io import BytesIO

from PIL import Image, UnidentifiedImageError

from app.core.logging import get_logger
from app.ml.preprocessing.exceptions import UnreadableImageError

logger = get_logger(__name__)


class PreprocessingReadabilityValidator:
    """Confirms uploaded image bytes are decodable immediately before preprocessing."""

    def validate_readable(self, image_bytes: bytes) -> Image.Image:
        """Decode `image_bytes` into a usable, loaded `PIL.Image.Image`.

        Args:
            image_bytes: Raw uploaded image bytes, already accepted by
                `UploadValidator` (ADR-011).

        Returns:
            A freshly opened and fully loaded PIL image, safe to pass into
            downstream preprocessing transforms.

        Raises:
            UnreadableImageError: If the bytes cannot be decoded or loaded.
        """
        try:
            image = Image.open(BytesIO(image_bytes))
            image.load()
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            logger.warning("Preprocessing rejected unreadable image data: %s", exc)
            raise UnreadableImageError() from exc

        return image
