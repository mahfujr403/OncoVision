"""Constants for centralized upload validation (ADR-011).

Re-exports the allow-lists that configure `app.core.upload.UploadValidator`
for domain-local, discoverable access from the Prediction API package. The
authoritative values live in `app.core.upload` -- see that module's
docstring for why the implementation is kept in `app.core` rather than
here -- so a future upload-accepting endpoint outside `predictions/` can
depend on the same single source of truth without importing this package.

Distinct from `app.constants.app.SUPPORTED_IMAGE_FORMATS`, which configures
the Prediction Engine's internal image validator
(`app.ml.prediction.validator.ImageValidator`, ADR-008) that inspects
already-accepted, decoded pixel data as part of inference. This module
governs the earlier, API-layer gate that inspects the raw upload
(extension and declared MIME type) before any prediction resources are
touched.
"""

from app.core.upload import SUPPORTED_EXTENSIONS, SUPPORTED_MIME_TYPES

__all__ = ["SUPPORTED_MIME_TYPES", "SUPPORTED_EXTENSIONS"]
