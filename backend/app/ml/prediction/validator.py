"""Uploaded image validation.

Validates raw uploaded image bytes before any preprocessing or inference
is attempted, so invalid input is rejected with a clear, descriptive error
before any model resources are touched.
"""

from io import BytesIO

from PIL import Image, UnidentifiedImageError

from app.constants.app import SUPPORTED_IMAGE_FORMATS
from app.core.logging import get_logger
from app.core.settings import get_settings
from app.ml.prediction.exceptions import (
    CorruptedImageError,
    EmptyUploadError,
    ImageResolutionError,
    ImageTooLargeError,
    UnsupportedImageFormatError,
)

logger = get_logger(__name__)


class ImageValidator:
    """Validates uploaded image bytes prior to preprocessing."""

    def validate(self, image_bytes: bytes) -> Image.Image:
        """Validate raw image bytes and return a freshly opened, usable image.

        Raises:
            EmptyUploadError: If `image_bytes` is empty.
            ImageTooLargeError: If `image_bytes` exceeds the configured maximum size.
            CorruptedImageError: If the bytes cannot be decoded as an image.
            UnsupportedImageFormatError: If the decoded format is not supported.
            ImageResolutionError: If the image resolution is outside the allowed range.
        """
        if not image_bytes:
            raise EmptyUploadError()

        settings = get_settings()
        if len(image_bytes) > settings.MAX_UPLOAD_SIZE:
            raise ImageTooLargeError(
                "The uploaded image exceeds the maximum allowed size of "
                f"{settings.MAX_UPLOAD_SIZE // (1024 * 1024)} MB."
            )

        image_format = self._decode_and_verify(image_bytes)
        if image_format not in SUPPORTED_IMAGE_FORMATS:
            raise UnsupportedImageFormatError(
                f"Unsupported image format '{image_format}'. Supported formats are: "
                f"{', '.join(sorted(SUPPORTED_IMAGE_FORMATS))}."
            )

        image = self._reopen(image_bytes)
        self._validate_resolution(
            image, settings.IMAGE_MIN_RESOLUTION, settings.IMAGE_MAX_RESOLUTION
        )
        return image

    def _decode_and_verify(self, image_bytes: bytes) -> str | None:
        """Decode and integrity-check the image, returning its detected format.

        Raises:
            CorruptedImageError: If the bytes cannot be decoded or fail integrity checks.
        """
        try:
            with Image.open(BytesIO(image_bytes)) as probe:
                image_format = probe.format
                probe.verify()
            return image_format
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            logger.warning("Rejected corrupted or unreadable image upload: %s", exc)
            raise CorruptedImageError() from exc

    def _reopen(self, image_bytes: bytes) -> Image.Image:
        """Re-open a fresh, usable image instance after `verify()` invalidated the prior one."""
        try:
            return Image.open(BytesIO(image_bytes))
        except (UnidentifiedImageError, OSError) as exc:
            raise CorruptedImageError() from exc

    def _validate_resolution(
        self, image: Image.Image, min_resolution: int, max_resolution: int
    ) -> None:
        """Ensure the image dimensions fall within the configured allowed range.

        Raises:
            ImageResolutionError: If the image is smaller or larger than allowed.
        """
        width, height = image.size
        if width < min_resolution or height < min_resolution:
            raise ImageResolutionError(
                f"Image resolution {width}x{height} is below the minimum allowed "
                f"resolution of {min_resolution}x{min_resolution}."
            )
        if width > max_resolution or height > max_resolution:
            raise ImageResolutionError(
                f"Image resolution {width}x{height} exceeds the maximum allowed "
                f"resolution of {max_resolution}x{max_resolution}."
            )
