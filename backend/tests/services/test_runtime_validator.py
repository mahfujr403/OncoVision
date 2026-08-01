"""Verification tests for the Phase 4.5.2 Runtime Validator (ADR-015).

Uses a lightweight fake `RuntimeAdapter` so these tests exercise only
`RuntimeValidator`'s own validation and error-mapping logic, independent
of `AIRuntimeManager` or `ModelRegistry` (already covered by
`tests/services/test_runtime_adapter.py`).

Not wired into a CI runner in this phase; run standalone with:
    PYTHONPATH=. python3 tests/services/test_runtime_validator.py
"""

import asyncio

from app.services.prediction_exceptions import (
    NoLoadedModelsError,
    RuntimeNotInitializedError,
    RuntimeValidationFailedError,
)
from app.services.runtime_adapter import RuntimeAvailability, RuntimeHealthSummary
from app.services.runtime_validator import RuntimeValidationResult, RuntimeValidator


class FakeRuntimeAdapter:
    """Duck-typed stand-in for `RuntimeAdapter`.

    Exposes only `get_runtime_health()`, the sole method `RuntimeValidator`
    is allowed to call, so an accidental call to any other adapter method
    (e.g. one that could trigger model access) fails the test loudly.
    """

    def __init__(self, health: RuntimeHealthSummary | None = None, raise_error: bool = False) -> None:
        self._health = health
        self._raise_error = raise_error

    async def get_runtime_health(self) -> RuntimeHealthSummary:
        if self._raise_error:
            raise ConnectionError("Simulated collaborator failure.")
        assert self._health is not None
        return self._health


def make_health(
    availability: RuntimeAvailability,
    is_initialized: bool,
    loaded_model_count: int,
    failed_model_count: int = 0,
) -> RuntimeHealthSummary:
    return RuntimeHealthSummary(
        availability=availability,
        is_initialized=is_initialized,
        loaded_model_count=loaded_model_count,
        failed_model_count=failed_model_count,
    )


def check(name: str, condition: bool) -> bool:
    print(f"[{'PASS' if condition else 'FAIL'}] {name}")
    return condition


async def run_case(name, coro_factory, expect_exception=None) -> bool:
    try:
        result = await coro_factory()
        if expect_exception is not None:
            print(f"[FAIL] {name}: expected {expect_exception.__name__}, got result {result}")
            return False
        print(f"[PASS] {name}: {result}")
        return True
    except Exception as exc:  # noqa: BLE001
        if expect_exception is not None and isinstance(exc, expect_exception):
            print(f"[PASS] {name}: raised {type(exc).__name__} -> {exc}")
            return True
        print(f"[FAIL] {name}: raised unexpected {type(exc).__name__} -> {exc}")
        return False


async def main() -> None:
    results: list[bool] = []

    # 1. Runtime initialized + healthy + one loaded model -> valid.
    one_model_validator = RuntimeValidator(
        FakeRuntimeAdapter(
            make_health(RuntimeAvailability.OPERATIONAL, is_initialized=True, loaded_model_count=1)
        )
    )
    one_model_result = await one_model_validator.validate()
    results.append(check(
        "Runtime initialized, healthy, one loaded model -> is_valid True",
        isinstance(one_model_result, RuntimeValidationResult)
        and one_model_result.is_valid is True
        and one_model_result.runtime_initialized is True
        and one_model_result.runtime_healthy is True
        and one_model_result.loaded_model_count == 1,
    ))

    # 2. Multiple loaded models, degraded (one failed) -> still valid.
    multi_model_validator = RuntimeValidator(
        FakeRuntimeAdapter(
            make_health(
                RuntimeAvailability.DEGRADED,
                is_initialized=True,
                loaded_model_count=2,
                failed_model_count=1,
            )
        )
    )
    multi_model_result = await multi_model_validator.validate()
    results.append(check(
        "Multiple loaded models, degraded but healthy -> is_valid True",
        multi_model_result.is_valid is True
        and multi_model_result.runtime_healthy is True
        and multi_model_result.loaded_model_count == 2
        and multi_model_result.failed_model_count == 1,
    ))

    # 3. Runtime not initialized -> invalid, specific message, specific exception.
    not_initialized_validator = RuntimeValidator(
        FakeRuntimeAdapter(
            make_health(RuntimeAvailability.UNAVAILABLE, is_initialized=False, loaded_model_count=0)
        )
    )
    not_initialized_result = await not_initialized_validator.validate()
    results.append(check(
        "Runtime not initialized -> is_valid False, runtime_initialized False",
        not_initialized_result.is_valid is False
        and not_initialized_result.runtime_initialized is False,
    ))
    results.append(await run_case(
        "validate_or_raise() raises RuntimeNotInitializedError when not initialized",
        not_initialized_validator.validate_or_raise,
        expect_exception=RuntimeNotInitializedError,
    ))

    # 4. Runtime initialized but zero loaded models -> invalid, NoLoadedModelsError.
    zero_model_validator = RuntimeValidator(
        FakeRuntimeAdapter(
            make_health(RuntimeAvailability.UNAVAILABLE, is_initialized=True, loaded_model_count=0)
        )
    )
    zero_model_result = await zero_model_validator.validate()
    results.append(check(
        "Zero loaded models detected -> is_valid False, loaded_model_count 0",
        zero_model_result.is_valid is False
        and zero_model_result.loaded_model_count == 0
        and zero_model_result.runtime_initialized is True,
    ))
    results.append(await run_case(
        "validate_or_raise() raises NoLoadedModelsError when zero models loaded",
        zero_model_validator.validate_or_raise,
        expect_exception=NoLoadedModelsError,
    ))

    # 5. Runtime unhealthy explicitly (initialized, but availability UNAVAILABLE
    #    despite a nonzero loaded count -- an edge case exercised directly at
    #    the validator level even though `RuntimeAdapter` does not currently
    #    produce it).
    unhealthy_validator = RuntimeValidator(
        FakeRuntimeAdapter(
            make_health(RuntimeAvailability.UNAVAILABLE, is_initialized=True, loaded_model_count=1)
        )
    )
    unhealthy_result = await unhealthy_validator.validate()
    results.append(check(
        "Runtime marked UNAVAILABLE -> runtime_healthy False regardless of loaded count",
        unhealthy_result.runtime_healthy is False
        and unhealthy_result.is_valid is False,
    ))

    # 6. Unexpected adapter failure -> RuntimeValidationFailedError, never leaks internals.
    broken_validator = RuntimeValidator(FakeRuntimeAdapter(raise_error=True))
    results.append(await run_case(
        "Unexpected RuntimeAdapter failure -> RuntimeValidationFailedError",
        broken_validator.validate,
        expect_exception=RuntimeValidationFailedError,
    ))

    # 7. RuntimeValidationResult serialization round-trip.
    dumped = one_model_result.model_dump()
    rebuilt = RuntimeValidationResult.model_validate(dumped)
    results.append(check(
        "RuntimeValidationResult serializes to a plain dict and back losslessly",
        dumped == {
            "is_valid": True,
            "runtime_initialized": True,
            "runtime_healthy": True,
            "loaded_model_count": 1,
            "failed_model_count": 0,
            "validation_message": one_model_result.validation_message,
        }
        and rebuilt == one_model_result,
    ))

    print()
    if all(results):
        print(f"ALL {len(results)} CASES PASSED")
    else:
        failed = len(results) - sum(results)
        print(f"{failed} / {len(results)} CASES FAILED")
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
