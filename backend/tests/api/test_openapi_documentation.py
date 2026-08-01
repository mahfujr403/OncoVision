"""Verification tests for Phase 4.9 OpenAPI Documentation (ADR-030).

Exercises the generated OpenAPI schema for `POST /api/v1/predictions`,
independent of any live HTTP server, following the same lightweight
pattern already used in `tests/api/test_runtime_statistics_integration.py`.

This phase is documentation-only (see `app.api.v1.predictions.router`'s
module docstring), so these checks intentionally assert on schema
*presence and shape* -- summary, description, tags, response schema,
status codes, and examples -- never on prediction, runtime, or
ensemble behavior, which are already covered by the Phase 4.1-4.8.3
test suites.

Not wired into a CI runner in this phase; run standalone with:
    PYTHONPATH=. python3 tests/api/test_openapi_documentation.py
"""

from app.constants.app import TAG_PREDICTIONS
from app.main import app

PREDICTIONS_PATH = "/api/v1/predictions"

# Every status code Phase 4.9 (ADR-030) requires to be documented for the
# prediction endpoint, regardless of whether current business logic can
# reach it today (see `router.py`'s `responses={...}` mapping and its
# per-code descriptions for the reserved/forward-compatible codes).
REQUIRED_STATUS_CODES = {
    "200",
    "400",
    "401",
    "404",
    "413",
    "415",
    "422",
    "429",
    "500",
    "503",
}

# Status codes that reflect real, currently reachable behavior and must
# therefore carry a concrete JSON example, not just a description.
STATUS_CODES_WITH_EXAMPLES = {"200", "400", "401", "422", "500", "503"}


def check(name: str, condition: bool) -> bool:
    print(f"[{'PASS' if condition else 'FAIL'}] {name}")
    return condition


def main() -> None:
    results: list[bool] = []

    # 1. The OpenAPI schema must generate successfully at all -- this is
    #    the same call FastAPI performs to serve /openapi.json and power
    #    the Swagger UI.
    schema = app.openapi()
    results.append(check("OpenAPI schema generates successfully", schema is not None))

    paths = schema.get("paths", {})
    results.append(
        check(
            f"'{PREDICTIONS_PATH}' is present in the OpenAPI schema",
            PREDICTIONS_PATH in paths,
        )
    )

    operation = paths.get(PREDICTIONS_PATH, {}).get("post", {})
    results.append(check("POST operation is documented", bool(operation)))

    # 2. Summary, description, and tag must all be present and non-trivial.
    results.append(
        check(
            "Operation has a non-empty 'summary'",
            bool(operation.get("summary")),
        )
    )
    description = operation.get("description", "")
    results.append(
        check(
            "Operation has a substantive 'description' (>200 chars)",
            len(description) > 200,
        )
    )
    results.append(
        check(
            f"Operation is tagged '{TAG_PREDICTIONS}'",
            TAG_PREDICTIONS in operation.get("tags", []),
        )
    )

    # 3. Multipart upload + request options must be documented as request
    #    body parameters (FastAPI documents `File`/`Form` params under
    #    `requestBody` for multipart/form-data operations).
    request_body = operation.get("requestBody", {})
    multipart_content = request_body.get("content", {}).get("multipart/form-data", {})
    results.append(
        check(
            "Request is documented as multipart/form-data",
            bool(multipart_content),
        )
    )
    form_schema_properties = multipart_content.get("schema", {}).get("properties", {})
    for expected_field in (
        "image",
        "confidence_threshold",
        "include_individual_predictions",
        "include_runtime_statistics",
        "save_history",
        "generate_report",
    ):
        results.append(
            check(
                f"Multipart schema documents '{expected_field}'",
                expected_field in form_schema_properties,
            )
        )

    # 4. Supported formats and maximum upload size must be discoverable
    #    from the documentation text itself.
    results.append(
        check(
            "Description documents supported image formats",
            "image/jpeg" in description
            and "image/png" in description
            and "image/tiff" in description,
        )
    )
    results.append(
        check(
            "Description documents the maximum upload size",
            "Maximum upload size" in description or "MB" in description,
        )
    )

    # 5. Every required status code must be documented on the operation.
    documented_responses = operation.get("responses", {})
    for status_code in sorted(REQUIRED_STATUS_CODES):
        results.append(
            check(
                f"Status code {status_code} is documented",
                status_code in documented_responses,
            )
        )

    # 6. Status codes representing real, reachable behavior must carry a
    #    concrete example (single `example` or named `examples`); reserved/
    #    forward-compatible codes (404, 413, 415, 429) only require a
    #    description, which was already verified above.
    for status_code in sorted(STATUS_CODES_WITH_EXAMPLES):
        content = documented_responses.get(status_code, {}).get("content", {})
        json_content = content.get("application/json", {})
        has_example = "example" in json_content or "examples" in json_content
        results.append(
            check(
                f"Status code {status_code} carries a concrete JSON example",
                has_example,
            )
        )

    # 7. Every documented status code must carry a non-empty description,
    #    including the reserved/forward-compatible ones.
    for status_code in sorted(REQUIRED_STATUS_CODES):
        entry = documented_responses.get(status_code, {})
        results.append(
            check(
                f"Status code {status_code} has a non-empty description",
                bool(entry.get("description")),
            )
        )

    # 8. The 200 response must reference a typed schema (response_model),
    #    not just a bare example, so Swagger renders a full response shape.
    success_content = documented_responses.get("200", {}).get("content", {})
    success_schema = success_content.get("application/json", {}).get("schema", {})
    results.append(
        check(
            "200 response references a typed response schema",
            bool(success_schema),
        )
    )

    print()
    if all(results):
        print(f"ALL {len(results)} CASES PASSED")
    else:
        failed = len(results) - sum(results)
        print(f"{failed} / {len(results)} CASES FAILED")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
