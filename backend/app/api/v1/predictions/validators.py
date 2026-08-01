"""Centralized upload validator for the Prediction API (ADR-011).

Re-exports `app.core.upload.UploadValidator` -- the shared validator every
upload-accepting endpoint must go through -- for domain-local,
discoverable access from the Prediction API package. The authoritative
implementation lives in `app.core.upload`; see that module's docstring
for why it is kept in `app.core` rather than here.

`PredictionService` receives its `UploadValidator` instance through
dependency injection (`app.dependencies.services.get_upload_validator`)
rather than importing this module directly, keeping the service
decoupled from any single API version's package layout.
"""

from app.core.upload import UploadValidationResult, UploadValidator

__all__ = ["UploadValidator", "UploadValidationResult"]
