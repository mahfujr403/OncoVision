"""Centralized upload validation (ADR-011).

Provides the single, reusable entry point for validating user-uploaded
medical images before they enter the prediction pipeline. Every endpoint
that accepts an image upload -- starting with the Prediction API, and
extending to future endpoints such as batch prediction, report upload, or
dataset management -- must validate through `UploadValidator` rather than
re-implementing validation logic in a router or service.

`UploadValidator` only inspects the upload itself: existence, declared
MIME type, extension, size, and basic image decodability/integrity. It
never resizes, normalizes, or otherwise preprocesses image data, and it
never performs inference. That remains the responsibility of the
Prediction Engine's own image validator
(`app.ml.prediction.validator.ImageValidator`, ADR-008), which runs later
in the pipeline against already-accepted image data.

Layering note: this module lives in `app.core` (not under
`app.api.v1.predictions`) even though ADR-011 was scoped around the
Prediction API, because it is constructed as a dependency very early in
the import graph (`app.dependencies.services` -> `app.dependencies.auth`).
Importing anything from `app.api.v1.predictions` here would pull in that
package's router -- which itself depends on `app.dependencies.auth` --
creating a circular import. Keeping the real implementation in `app.core`
(the lower architectural layer) and re-exporting it from
`app.api.v1.predictions.constants`, `.exceptions`, and `.validators` for
domain-local, discoverable access keeps the dependency direction correct:
`app.api` may depend on `app.core`, never the reverse.
"""

from io import BytesIO
from typing import Final

from fastapi import UploadFile, status
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field

from app.core.exceptions import OncoVisionError
from app.core.logging import get_logger
from app.core.settings import get_settings

logger = get_logger(__name__)

VALID_STATUS: str = "valid"

SUPPORTED_MIME_TYPES: Final[frozenset[str]] = frozenset(
    {"image/jpeg", "image/png", "image/tiff"}
)

SUPPORTED_EXTENSIONS: Final[frozenset[str]] = frozenset(
    {"jpg", "jpeg", "png", "tif", "tiff"}
)

# Maximum upload size is intentionally not duplicated here. It is already
# centrally defined as `Settings.MAX_UPLOAD_SIZE` (`app.core.settings`),
# which remains the single source of truth for that value across the
# application.


class UploadValidationException(OncoVisionError):
    """Base exception for centralized upload validation failures."""

    def __init__(self, message: str = "The uploaded file is invalid.") -> None:
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST)


class MissingImageException(UploadValidationException):
    """Raised when no image file was included in the request."""

    def __init__(self, message: str = "No image file was provided.") -> None:
        super().__init__(message=message)


class EmptyFileException(UploadValidationException):
    """Raised when the uploaded file contains no data."""

    def __init__(self, message: str = "The uploaded file is empty.") -> None:
        super().__init__(message=message)


class UnsupportedFileTypeException(UploadValidationException):
    """Raised when the uploaded file's extension or MIME type is not supported."""

    def __init__(
        self, message: str = "The uploaded file type is not supported."
    ) -> None:
        super().__init__(message=message)


class FileTooLargeException(UploadValidationException):
    """Raised when the uploaded file exceeds the maximum allowed upload size."""

    def __init__(
        self, message: str = "The uploaded file exceeds the maximum allowed size."
    ) -> None:
        super().__init__(message=message)


class InvalidImageException(UploadValidationException):
    """Raised when the uploaded file fails image integrity verification."""

    def __init__(
        self, message: str = "The uploaded file is not a valid image."
    ) -> None:
        super().__init__(message=message)


class CorruptedImageException(UploadValidationException):
    """Raised when the uploaded image data cannot be decoded."""

    def __init__(
        self, message: str = "The uploaded image is corrupted or unreadable."
    ) -> None:
        super().__init__(message=message)


class UploadValidationResult(BaseModel):
    """Outcome of a successful centralized upload validation.

    Only ever constructed after every validation rule has passed; any
    failed rule raises a dedicated exception instead. Immutable so
    downstream services can safely treat it as a trusted, reusable
    description of the upload without risk of accidental mutation.
    """

    model_config = ConfigDict(frozen=True)

    original_filename: str = Field(description="Filename as provided by the client.")
    content_type: str = Field(description="MIME type declared by the client.")
    file_size: int = Field(description="Uploaded file size, in bytes.")
    extension: str = Field(description="Lowercased file extension, without the leading dot.")
    width: int = Field(description="Image width, in pixels.")
    height: int = Field(description="Image height, in pixels.")
    status: str = Field(default=VALID_STATUS, description="Validation outcome status.")


class UploadValidator:
    """Validates uploaded medical images before they enter the prediction pipeline.

    Consumed by the Prediction API -- and any future upload-accepting API --
    through a single shared code path, per ADR-011. Stateless and safe to
    reuse across requests.
    """

    async def validate(self, image: UploadFile | None) -> UploadValidationResult:
        """Validate an uploaded image and return its trusted metadata.

        Args:
            image: The uploaded file, as provided by FastAPI's `File(...)`.

        Returns:
            An `UploadValidationResult` describing the accepted upload.

        Raises:
            MissingImageException: If no file was uploaded.
            UnsupportedFileTypeException: If the extension or MIME type is not supported.
            EmptyFileException: If the uploaded file contains no data.
            FileTooLargeException: If the file exceeds the configured maximum size.
            CorruptedImageException: If the image data cannot be decoded.
            InvalidImageException: If the image fails integrity verification.
        """
        self._validate_presence(image)
        extension = self._validate_extension(image.filename)
        self._validate_mime_type(image.content_type)

        contents = await image.read()
        await image.seek(0)

        self._validate_not_empty(contents)
        self._validate_size(contents)
        width, height = self._validate_image_data(contents)

        logger.info(
            "Upload validation passed: filename=%s size=%d extension=%s",
            image.filename,
            len(contents),
            extension,
        )

        return UploadValidationResult(
            original_filename=image.filename,
            content_type=image.content_type,
            file_size=len(contents),
            extension=extension,
            width=width,
            height=height,
        )

    def _validate_presence(self, image: UploadFile | None) -> None:
        """Ensure a file was actually uploaded.

        Raises:
            MissingImageException: If `image` is missing or has no filename.
        """
        if image is None or not image.filename:
            raise MissingImageException()

    def _validate_extension(self, filename: str) -> str:
        """Ensure the filename has a supported extension.

        Raises:
            UnsupportedFileTypeException: If the extension is missing or unsupported.

        Returns:
            The lowercased extension, without the leading dot.
        """
        if "." not in filename:
            raise UnsupportedFileTypeException(
                f"File '{filename}' has no extension. Supported extensions are: "
                f"{', '.join(sorted(SUPPORTED_EXTENSIONS))}."
            )
        extension = filename.rsplit(".", 1)[-1].lower()
        if extension not in SUPPORTED_EXTENSIONS:
            raise UnsupportedFileTypeException(
                f"Unsupported file extension '.{extension}'. Supported extensions are: "
                f"{', '.join(sorted(SUPPORTED_EXTENSIONS))}."
            )
        return extension

    def _validate_mime_type(self, content_type: str | None) -> None:
        """Ensure the declared MIME type is supported.

        Raises:
            UnsupportedFileTypeException: If the MIME type is missing or unsupported.
        """
        if content_type not in SUPPORTED_MIME_TYPES:
            raise UnsupportedFileTypeException(
                f"Unsupported content type '{content_type}'. Supported types are: "
                f"{', '.join(sorted(SUPPORTED_MIME_TYPES))}."
            )

    def _validate_not_empty(self, contents: bytes) -> None:
        """Ensure the uploaded file contains data.

        Raises:
            EmptyFileException: If `contents` is empty.
        """
        if not contents:
            raise EmptyFileException()

    def _validate_size(self, contents: bytes) -> None:
        """Ensure the uploaded file does not exceed the configured maximum size.

        Raises:
            FileTooLargeException: If `contents` exceeds `settings.MAX_UPLOAD_SIZE`.
        """
        settings = get_settings()
        if len(contents) > settings.MAX_UPLOAD_SIZE:
            raise FileTooLargeException(
                "The uploaded file exceeds the maximum allowed size of "
                f"{settings.MAX_UPLOAD_SIZE // (1024 * 1024)} MB."
            )

    def _validate_image_data(self, contents: bytes) -> tuple[int, int]:
        """Ensure the uploaded bytes decode as a valid, readable image.

        Raises:
            CorruptedImageException: If the bytes cannot be decoded at all.
            InvalidImageException: If the image fails integrity verification.

        Returns:
            The image's `(width, height)`, in pixels.
        """
        try:
            with Image.open(BytesIO(contents)) as probe:
                probe.verify()
        except UnidentifiedImageError as exc:
            logger.warning("Rejected upload with undecodable image data: %s", exc)
            raise CorruptedImageException() from exc
        except (OSError, ValueError) as exc:
            logger.warning("Rejected upload that failed image integrity checks: %s", exc)
            raise InvalidImageException() from exc

        try:
            with Image.open(BytesIO(contents)) as reopened:
                return reopened.size
        except (UnidentifiedImageError, OSError) as exc:
            logger.warning("Failed to re-open validated image to read dimensions: %s", exc)
            raise CorruptedImageException() from exc
