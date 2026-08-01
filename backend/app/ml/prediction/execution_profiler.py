"""Execution Profiler (Phase 4.6.6 - Runtime Statistics & Performance Metrics).

`ExecutionProfiler` is the single reusable place pipeline stage durations
are measured for a single prediction request. It performs no AI
inference, no image preprocessing, and never communicates with the AI
Runtime Manager, Prediction Engine, or Adaptive Ensemble Engine -- it
only records wall-clock timestamps and durations around code that
`PredictionService` already executes for the PREPROCESSING, RUNTIME, and
REQUEST_BUILDING pipeline stages (ADR-013).

`PredictionService` constructs exactly one `ExecutionProfiler` per
request and threads it through each stage method, wrapping the existing
stage logic in `profiler.measure(...)` rather than duplicating timing
code inline. `ExecutionStatistics` (Phase 4.6.5, ADR-022) already
aggregates per-model outcome counts; this module adds the complementary
per-stage timing view that `RuntimeStatistics`
(`app.ml.prediction.runtime_statistics`) consumes to build a complete
execution metrics snapshot.

Future phases reuse this same module without change:
    - Phase 4.7 (Adaptive Ensemble Integration) may profile ensemble
      aggregation the same way, by measuring an additional stage.
"""

import time
from contextlib import contextmanager
from enum import Enum
from typing import Iterator

from pydantic import BaseModel, ConfigDict, Field

from app.core.logging import get_logger
from app.utils.environment import get_current_timestamp

logger = get_logger(__name__)


class ProfiledStage(str, Enum):
    """Identifies a single stage measured by `ExecutionProfiler`.

    Intentionally distinct from `app.services.prediction_result.PipelineStageName`:
    that enum records completed/skipped bookkeeping for every pipeline
    stage, while this enum only labels the subset of stages whose
    wall-clock duration is profiled for `RuntimeStatistics`.
    """

    PREPROCESSING = "preprocessing"
    RUNTIME_VALIDATION = "runtime_validation"
    REQUEST_BUILDING = "request_building"
    PREDICTION_ENGINE = "prediction_engine"


class StageTiming(BaseModel):
    """Recorded wall-clock duration of a single profiled pipeline stage."""

    model_config = ConfigDict(frozen=True)

    stage_name: str = Field(description="Identifier of the profiled stage.")
    started_at: str = Field(description="ISO 8601 timestamp the stage started.")
    completed_at: str = Field(description="ISO 8601 timestamp the stage completed.")
    duration_ms: float = Field(description="Wall-clock duration of the stage, in milliseconds.")


class ExecutionProfile(BaseModel):
    """Serializable, ordered record of every profiled stage for a single request.

    Produced exactly once per request by `ExecutionProfiler.complete()`.
    Carries no live timer state -- only plain, serializable timestamps
    and durations -- so it can be attached to `PredictionExecutionResult`
    (Phase 4.6.5/4.6.6, ADR-022) or logged directly.
    """

    model_config = ConfigDict(frozen=True)

    request_id: str = Field(description="Unique identifier for the profiled prediction request.")
    profile_started_at: str = Field(
        description="ISO 8601 timestamp profiling began for this request."
    )
    profile_completed_at: str | None = Field(
        default=None,
        description="ISO 8601 timestamp profiling completed, or None while still in progress.",
    )
    stages: list[StageTiming] = Field(
        description="Every profiled stage, in the order it was measured."
    )
    total_duration_ms: float | None = Field(
        default=None,
        description=(
            "Total wall-clock duration from profiling start to completion, "
            "in milliseconds, or None while still in progress."
        ),
    )

    def get_stage_duration_ms(self, stage_name: str) -> float:
        """Return the recorded duration for `stage_name`, or 0.0 if never measured."""
        for stage in self.stages:
            if stage.stage_name == stage_name:
                return stage.duration_ms
        return 0.0


class ExecutionProfiler:
    """Measures and records stage durations for a single prediction request.

    Stateful for the lifetime of one request only: constructed once by
    `PredictionService` at the start of `predict()`, threaded through each
    stage method, and finalized once via `complete()`. Never shared across
    requests and never touches the AI Runtime Manager, Prediction Engine,
    or Adaptive Ensemble Engine.
    """

    def __init__(self, request_id: str) -> None:
        self._request_id = request_id
        self._profile_started_perf = time.perf_counter()
        self._profile_started_at = get_current_timestamp()
        self._stages: list[StageTiming] = []

    @contextmanager
    def measure(self, stage_name: str) -> Iterator[None]:
        """Measure the wall-clock duration of the code executed inside this context.

        Usage:
            with profiler.measure(ProfiledStage.PREPROCESSING):
                ... existing stage logic, may freely `await` coroutines ...

        Only the context manager protocol itself is synchronous; the
        measured block may contain `await` expressions exactly as before,
        since this method changes nothing about how the wrapped code runs.
        The measured duration is always recorded, even if the wrapped code
        raises, so a stage that fails still contributes an accurate timing
        entry.
        """
        started_at = get_current_timestamp()
        started_perf = time.perf_counter()
        try:
            yield
        finally:
            duration_ms = round((time.perf_counter() - started_perf) * 1000, 2)
            completed_at = get_current_timestamp()
            self._stages.append(
                StageTiming(
                    stage_name=str(stage_name),
                    started_at=started_at,
                    completed_at=completed_at,
                    duration_ms=duration_ms,
                )
            )
            logger.info(
                "Stage profiled: request_id=%s stage=%s duration_ms=%.2f",
                self._request_id,
                stage_name,
                duration_ms,
            )

    def get_stage_duration_ms(self, stage_name: str) -> float:
        """Return the recorded duration for `stage_name`, or 0.0 if never measured."""
        for stage in self._stages:
            if stage.stage_name == str(stage_name):
                return stage.duration_ms
        return 0.0

    def elapsed_ms(self) -> float:
        """Return wall-clock milliseconds elapsed since this profiler was created."""
        return round((time.perf_counter() - self._profile_started_perf) * 1000, 2)

    def build_profile(self) -> ExecutionProfile:
        """Return a serializable, still-in-progress snapshot of every stage measured so far.

        Unlike `complete()`, this never finalizes `profile_completed_at` or
        `total_duration_ms`; useful for diagnostics mid-pipeline.
        """
        return ExecutionProfile(
            request_id=self._request_id,
            profile_started_at=self._profile_started_at,
            profile_completed_at=None,
            stages=list(self._stages),
            total_duration_ms=None,
        )

    def complete(self) -> ExecutionProfile:
        """Finalize profiling and return the complete `ExecutionProfile` for this request.

        Safe to call more than once: each call recomputes
        `total_duration_ms` against the current elapsed time and returns a
        fresh, independent `ExecutionProfile` snapshot.
        """
        total_duration_ms = self.elapsed_ms()
        profile = ExecutionProfile(
            request_id=self._request_id,
            profile_started_at=self._profile_started_at,
            profile_completed_at=get_current_timestamp(),
            stages=list(self._stages),
            total_duration_ms=total_duration_ms,
        )
        logger.info(
            "Execution profile completed: request_id=%s stage_count=%d total_duration_ms=%.2f",
            self._request_id,
            len(self._stages),
            total_duration_ms,
        )
        return profile
