"""OpenAPI/Swagger documentation examples for the Prediction API (Phase 4.3).

Plain dictionaries only -- no schema construction or validation happens
here. Each constant is wired into `router.py`'s `responses={...}` mapping
so Swagger renders a concrete example for every documented status code,
following the same pattern already used for the Phase 4.2 upload
validation responses.

Phase 4.9 (ADR-030) extends this module with additional named examples --
`FILE_TOO_LARGE_EXAMPLE` and `REQUEST_FIELD_VALIDATION_ERROR_EXAMPLE` --
so Swagger can illustrate more than one concrete failure shape per status
code (e.g. `400` covers both an unsupported file type and an oversized
file). No new status codes or error-handling behavior are introduced;
these are documentation-only projections of exception shapes that
already exist as of Phase 4.2/4.3 (`app.core.upload`,
`app.core.exceptions.validation_exception_handler`).
"""

from typing import Any, Final

REQUEST_EXAMPLE: Final[dict[str, Any]] = {
    "confidence_threshold": 0.5,
    "include_individual_predictions": True,
    "include_runtime_statistics": False,
    "save_history": True,
    "generate_report": False,
}

SUCCESS_RESPONSE_EXAMPLE: Final[dict[str, Any]] = {
    "success": True,
    "message": "Prediction request received.",
    "data": {
        "prediction_id": "b1f0c6b2-5c1a-4e9e-9c3a-2f6a0e0f9a11",
        "status": "pending",
        "message": "Image validation successful.",
        "timestamp": "2026-07-19T10:00:00Z",
        "result": None,
        "individual_predictions": None,
        "runtime_statistics": None,
        "metadata": {
            "api_version": "v1",
            "backend_version": "1.0.0",
            "model_manifest_version": None,
            "processing_time_ms": 12.7,
        },
    },
    "errors": None,
    "request_id": "b1f0c6b2-5c1a-4e9e-9c3a-2f6a0e0f9a11",
    "timestamp": "2026-07-19T10:00:00Z",
}

VALIDATION_ERROR_EXAMPLE: Final[dict[str, Any]] = {
    "success": False,
    "message": "The uploaded file failed centralized upload validation.",
    "data": None,
    "errors": [
        {
            "code": "validation_error",
            "field": "image",
            "message": "Unsupported file type. Allowed types: JPEG, PNG, TIFF.",
        }
    ],
    "request_id": "0f3f6a1a-6a3f-4e2a-8f0e-6a6a6a6a6a6a",
    "timestamp": "2026-07-19T10:00:05Z",
}

# Same `400` status as `VALIDATION_ERROR_EXAMPLE` -- both are raised by the
# same centralized `UploadValidator` (ADR-011) -- but illustrates the
# maximum-upload-size rule specifically (`Settings.MAX_UPLOAD_SIZE`, 10 MB
# by default) rather than an unsupported file type.
FILE_TOO_LARGE_EXAMPLE: Final[dict[str, Any]] = {
    "success": False,
    "message": "The uploaded file exceeds the maximum allowed size.",
    "data": None,
    "errors": [
        {
            "code": "validation_error",
            "field": "image",
            "message": "The uploaded file exceeds the maximum allowed size of 10 MB.",
        }
    ],
    "request_id": "4d5e6f7a-8b9c-4d0e-1f2a-3b4c5d6e7f80",
    "timestamp": "2026-07-19T10:00:05Z",
}

# Distinct from the `400` upload-validation examples above: this is a
# `422` produced by FastAPI/Pydantic request-field validation
# (`app.core.exceptions.validation_exception_handler`) rather than by
# `UploadValidator`, so it carries no `code` key -- matching the handler's
# actual `{"field": ..., "message": ...}` error shape.
REQUEST_FIELD_VALIDATION_ERROR_EXAMPLE: Final[dict[str, Any]] = {
    "success": False,
    "message": "Request validation failed.",
    "data": None,
    "errors": [
        {
            "field": "body.confidence_threshold",
            "message": "Input should be less than or equal to 1",
        }
    ],
    "request_id": "5e6f7a8b-9c0d-4e1f-2a3b-4c5d6e7f8091",
    "timestamp": "2026-07-19T10:00:05Z",
}

AUTHENTICATION_ERROR_EXAMPLE: Final[dict[str, Any]] = {
    "success": False,
    "message": "Authentication is required to access this resource.",
    "data": None,
    "errors": [
        {
            "code": "authentication_error",
            "field": None,
            "message": "Missing or invalid authentication credentials.",
        }
    ],
    "request_id": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
    "timestamp": "2026-07-19T10:00:05Z",
}

PREDICTION_UNAVAILABLE_EXAMPLE: Final[dict[str, Any]] = {
    "success": False,
    "message": "No production models are currently available to serve predictions.",
    "data": None,
    "errors": [
        {
            "code": "prediction_error",
            "field": None,
            "message": "All registered models failed to load or are disabled.",
        }
    ],
    "request_id": "2b3c4d5e-6f7a-4b8c-9d0e-1f2a3b4c5d6e",
    "timestamp": "2026-07-19T10:00:05Z",
}

INTERNAL_ERROR_EXAMPLE: Final[dict[str, Any]] = {
    "success": False,
    "message": "An unexpected internal server error occurred.",
    "data": None,
    "errors": None,
    "request_id": "3c4d5e6f-7a8b-4c9d-0e1f-2a3b4c5d6e7f",
    "timestamp": "2026-07-19T10:00:05Z",
}
