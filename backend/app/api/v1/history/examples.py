"""OpenAPI/Swagger documentation examples for the Prediction History API (Phase 5.4, ADR-035).

Plain dictionaries only -- no schema construction or validation happens
here, mirroring `app.api.v1.predictions.examples`. Each constant is wired
into `router.py`'s `responses={...}` mapping so Swagger renders a concrete
example for every documented status code.

`FILTER_VALIDATION_ERROR_EXAMPLE` illustrates the `422` produced when a
`PredictionHistoryFilter` or `PredictionHistoryPageRequest` is constructed
from an internally inconsistent combination of query parameters (e.g.
`start_date` later than `end_date`, or `page_size` outside its allowed
range) -- the same `app.core.exceptions.validation_exception_handler`
already documented for the Prediction API's own `422` response.
"""

from typing import Any, Final

FILTER_VALIDATION_ERROR_EXAMPLE: Final[dict[str, Any]] = {
    "success": False,
    "message": "Request validation failed.",
    "data": None,
    "errors": [
        {
            "field": "start_date must not be later than end_date.",
            "message": "Value error, start_date must not be later than end_date.",
        }
    ],
    "request_id": "6f7a8b9c-0d1e-4f2a-3b4c-5d6e7f809162",
    "timestamp": "2026-07-19T10:00:05Z",
}
