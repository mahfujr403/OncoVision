"""Verification tests for the Phase 4.4 Prediction Service skeleton (ADR-013).

Not wired into a CI runner in this phase; run standalone with:
    PYTHONPATH=. python3 tests/services/test_prediction_service.py
"""

import asyncio
import io
import uuid

from PIL import Image
from starlette.datastructures import Headers, UploadFile

from app.api.v1.predictions.schemas import PredictionRequestSchema
from app.core.upload import UploadValidator
from app.ml.ensemble.final_prediction_builder import FinalPredictionBuilder
from app.models.enums import UserRole
from app.models.user import User
from app.services.prediction_context import PredictionContext, PredictionOptions
from app.services.prediction_result import PipelineStageName, PipelineStageStatus
from app.services.prediction_service import PredictionService


def make_upload_file(filename: str, content: bytes, content_type: str) -> UploadFile:
    headers = Headers({"content-type": content_type})
    return UploadFile(filename=filename, file=io.BytesIO(content), headers=headers)


def make_valid_image_bytes(fmt: str, size: tuple[int, int] = (64, 64)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color=(10, 90, 140)).save(buffer, format=fmt)
    return buffer.getvalue()


def make_test_user() -> User:
    return User(
        id=uuid.uuid4(),
        full_name="Test Pathologist",
        email="pathologist@example.com",
        password_hash="hashed",
        role=UserRole.USER,
        is_active=True,
    )


async def run_case(name, coro_factory, expect_exception=None):
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


def check(name: str, condition: bool) -> bool:
    print(f"[{'PASS' if condition else 'FAIL'}] {name}")
    return condition


async def main() -> None:
    results: list[bool] = []

    service = PredictionService(upload_validator=UploadValidator())

    # 1. PredictionOptions creation from a validated PredictionRequestSchema.
    request_schema = PredictionRequestSchema()
    options = PredictionOptions.from_request(request_schema)
    results.append(check(
        "PredictionOptions.from_request mirrors PredictionRequestSchema",
        options.confidence_threshold == request_schema.confidence_threshold
        and options.include_individual_predictions == request_schema.include_individual_predictions,
    ))

    # 2. PredictionContext creation from validated upload metadata.
    validator = UploadValidator()
    upload = make_upload_file("slide.png", make_valid_image_bytes("PNG"), "image/png")
    validation = await validator.validate(upload)
    context = PredictionContext.from_validated_upload(
        request_id="test-request-id",
        requested_at="2026-07-19T00:00:00+00:00",
        user_id="test-user-id",
        user_email="pathologist@example.com",
        validation=validation,
        options=options,
    )
    results.append(check(
        "PredictionContext carries validated upload metadata",
        context.image_filename == "slide.png"
        and context.image_width == 64
        and context.image_height == 64
        and context.options is options,
    ))

    # 3. PredictionResult serialization.
    upload_for_service = make_upload_file("slide.jpg", make_valid_image_bytes("JPEG"), "image/jpeg")
    user = make_test_user()
    prediction_result = await service.predict(
        image=upload_for_service, current_user=user, options=options
    )
    serialized = prediction_result.model_dump(mode="json")
    results.append(check(
        "PredictionResult serializes to a JSON-compatible dict",
        isinstance(serialized, dict) and serialized["request_id"] == prediction_result.request_id,
    ))

    # 4. Placeholder response: every stage recorded, correct completed/skipped split.
    stage_names = {stage.name for stage in prediction_result.stages}
    completed = {
        stage.name for stage in prediction_result.stages
        if stage.status == PipelineStageStatus.COMPLETED
    }
    skipped = {
        stage.name for stage in prediction_result.stages
        if stage.status == PipelineStageStatus.SKIPPED
    }
    results.append(check(
        "All nine pipeline stages are recorded exactly once",
        stage_names == set(PipelineStageName) and len(prediction_result.stages) == len(PipelineStageName),
    ))
    results.append(check(
        "Only upload_validation and context_creation completed; the rest are skipped",
        completed == {PipelineStageName.UPLOAD_VALIDATION, PipelineStageName.CONTEXT_CREATION}
        and skipped == set(PipelineStageName) - completed,
    ))
    results.append(check(
        "Downstream outcome fields remain null placeholders",
        prediction_result.prediction is None
        and prediction_result.confidence is None
        and prediction_result.individual_model_results is None
        and prediction_result.ensemble_result is None
        and prediction_result.final_prediction_result is None
        and prediction_result.runtime_statistics is None
        and prediction_result.history_reference is None
        and prediction_result.report_reference is None,
    ))

    # 5. Dependency injection: future modules are optional and injectable
    #    without changing the constructor signature.
    service_with_future_deps = PredictionService(
        upload_validator=UploadValidator(),
        runtime_manager=None,
        prediction_engine=None,
        ensemble_engine=None,
        voting_engine=None,
        calibration_engine=None,
        final_prediction_builder=None,
    )
    results.append(check(
        "PredictionService accepts future ML modules as optional dependencies",
        service_with_future_deps._runtime_manager is None
        and service_with_future_deps._prediction_engine is None
        and service_with_future_deps._ensemble_engine is None
        and service_with_future_deps._voting_engine is None
        and service_with_future_deps._calibration_engine is None
        and service_with_future_deps._final_prediction_builder is None,
    ))

    # 6. Upload validation failures still propagate through the service.
    from app.core.upload import UnsupportedFileTypeException

    async def invalid_upload():
        bad_upload = make_upload_file("scan.bmp", make_valid_image_bytes("BMP"), "image/bmp")
        return await service.predict(image=bad_upload, current_user=user, options=options)

    results.append(await run_case(
        "Invalid upload still raises before context creation",
        invalid_upload,
        expect_exception=UnsupportedFileTypeException,
    ))

    # 7. Phase 4.7.4.2: the internal FINAL_PREDICTION step chains voting,
    #    calibration, and final-prediction building, in order, once all
    #    three collaborators are injected and the ENSEMBLE stage output
    #    is available. Uses lightweight test doubles so this checks
    #    PredictionService's own orchestration logic (call order, `None`
    #    propagation, exception wrapping) independent of the real voting/
    #    calibration math already covered by their own unit tests.
    from app.ml.ensemble.calibration_result import AgreementStatistics, CalibratedEnsembleResult
    from app.ml.ensemble.exceptions import InvalidEnsembleInputError
    from app.ml.ensemble.voting_result import VotingResult
    from app.services.prediction_exceptions import EnsembleUnavailableError

    class FakeVotingEngine:
        def calculate_votes(self, engine_result):
            return VotingResult.empty()

    class FakeCalibrationEngine:
        def calibrate(self, voting_result):
            return CalibratedEnsembleResult(
                winning_class="lung_adenocarcinoma",
                calibrated_confidence=91.25,
                agreement_statistics=AgreementStatistics(
                    successful_models=["mobilenet_v2"],
                    failed_models=[],
                    total_models=1,
                    agreement_ratio=1.0,
                ),
                weighted_votes=[],
            )

    class FakeFailingCalibrationEngine:
        def calibrate(self, voting_result):
            raise InvalidEnsembleInputError("forced failure for test coverage")

    service_with_final_prediction = PredictionService(
        upload_validator=UploadValidator(),
        voting_engine=FakeVotingEngine(),
        calibration_engine=FakeCalibrationEngine(),
        final_prediction_builder=FinalPredictionBuilder(),
    )

    async def run_final_prediction_stage():
        return await service_with_final_prediction._execute_final_prediction_stage(
            context=context,
            prediction_engine_result=object(),
            ensemble_result=object(),
        )

    final_prediction_result = await run_final_prediction_stage()
    results.append(check(
        "Final prediction step builds a FinalPredictionResult from the chained collaborators",
        final_prediction_result is not None
        and final_prediction_result.predicted_class == "lung_adenocarcinoma"
        and final_prediction_result.confidence == 91.25
        and final_prediction_result.agreement_ratio == 1.0,
    ))

    async def run_final_prediction_stage_missing_ensemble():
        return await service_with_final_prediction._execute_final_prediction_stage(
            context=context,
            prediction_engine_result=object(),
            ensemble_result=None,
        )

    results.append(check(
        "Final prediction step is skipped (returns None) without a completed ENSEMBLE stage",
        await run_final_prediction_stage_missing_ensemble() is None,
    ))

    service_without_final_prediction_deps = PredictionService(upload_validator=UploadValidator())

    async def run_final_prediction_stage_unwired():
        return await service_without_final_prediction_deps._execute_final_prediction_stage(
            context=context,
            prediction_engine_result=object(),
            ensemble_result=object(),
        )

    results.append(check(
        "Final prediction step is skipped (returns None) when its collaborators are not injected",
        await run_final_prediction_stage_unwired() is None,
    ))

    service_with_failing_calibration = PredictionService(
        upload_validator=UploadValidator(),
        voting_engine=FakeVotingEngine(),
        calibration_engine=FakeFailingCalibrationEngine(),
        final_prediction_builder=FinalPredictionBuilder(),
    )

    async def run_final_prediction_stage_failure():
        return await service_with_failing_calibration._execute_final_prediction_stage(
            context=context,
            prediction_engine_result=object(),
            ensemble_result=object(),
        )

    results.append(await run_case(
        "Final prediction step wraps collaborator failures as EnsembleUnavailableError",
        run_final_prediction_stage_failure,
        expect_exception=EnsembleUnavailableError,
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
