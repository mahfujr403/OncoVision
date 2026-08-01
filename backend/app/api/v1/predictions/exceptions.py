"""Centralized upload validation exceptions (ADR-011).

Re-exports the exception types raised by
`app.core.upload.UploadValidator` for domain-local, discoverable access
from the Prediction API package. The authoritative classes live in
`app.core.upload` -- see that module's docstring for why the
implementation is kept in `app.core` rather than here.

Each exception extends the application's centralized `OncoVisionError` so
it is handled automatically by the existing global exception handlers
(`app.core.exceptions`) and never leaks internal details to API clients.

These are distinct from `app.ml.prediction.exceptions`, which cover the
Prediction Engine's internal image validation (ADR-008) that runs later,
against already-accepted image data, as part of inference.
"""

from app.core.upload import (
    CorruptedImageException,
    EmptyFileException,
    FileTooLargeException,
    InvalidImageException,
    MissingImageException,
    UnsupportedFileTypeException,
    UploadValidationException,
)

__all__ = [
    "UploadValidationException",
    "MissingImageException",
    "EmptyFileException",
    "UnsupportedFileTypeException",
    "FileTooLargeException",
    "InvalidImageException",
    "CorruptedImageException",
]
