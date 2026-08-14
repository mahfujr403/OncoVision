"""FastAPI dependency providers for service instances."""

from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.upload import UploadValidator
from app.core.request_metrics import default_request_metrics_collector
from app.database.database import get_db
from app.ml.cache.cache_manager import ModelCacheManager
from app.ml.downloader.download_manager import ModelDownloadManager
from app.ml.downloader.huggingface_downloader import HuggingFaceDownloader
from app.ml.ensemble.calibration_engine import ConfidenceCalibrationEngine
from app.ml.ensemble.ensemble_engine import AdaptiveEnsembleEngine, EnsembleEngine
from app.ml.ensemble.final_prediction_builder import FinalPredictionBuilder
from app.ml.ensemble.voting_engine import AdaptiveWeightedVotingEngine
from app.ml.metadata.metadata_service import ModelMetadataService
from app.ml.prediction.prediction_engine import PredictionEngine
from app.ml.prediction.prediction_execution_result import PredictionResultCollector
from app.ml.prediction.request_builder import PredictionRequestBuilder
from app.ml.preprocessing.image_preprocessor import ImagePreprocessor
from app.ml.registry.manifest_loader import load_manifest
from app.ml.registry.model_registry import ModelRegistry
from app.ml.response.response_builder import PredictionResponseBuilder
from app.ml.runtime.runtime_manager import AIRuntimeManager
from app.repositories.prediction_history_repository import (
    PredictionHistoryRepository,
    SQLAlchemyPredictionHistoryRepository,
)
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.reports.analytics.analytics_builder import AnalyticsBuilder
from app.reports.analytics.analytics_validator import AnalyticsValidator
from app.reports.builder import ReportBuilder
from app.reports.csv.csv_builder import CSVExportBuilder
from app.reports.csv.csv_validator import CSVValidator
from app.reports.pdf.pdf_builder import PDFBuilder
from app.reports.pdf.pdf_validator import PDFValidator
from app.reports.validator import ReportValidator
from app.services.admin_history_service import AdminHistoryService
from app.services.admin_system_service import AdminSystemService
from app.services.admin_user_service import AdminUserService
from app.services.auth_service import AuthService
from app.services.jwt_service import JWTService
from app.services.monitoring_service import MonitoringService
from app.services.password_service import PasswordService
from app.services.prediction_analytics_service import PredictionAnalyticsService
from app.services.prediction_history_service import PredictionHistoryService
from app.services.prediction_service import PredictionService
from app.reports.csv.csv_export_service import CSVExportService
from app.reports.pdf.pdf_export_service import PDFExportService
from app.services.report_service import ReportService
from app.services.runtime_adapter import RuntimeAdapter
from app.services.runtime_metadata import RuntimeMetadataService
from app.services.runtime_validator import RuntimeValidator
from app.services.system_service import SystemService


@lru_cache
def get_system_service() -> SystemService:
    """Provide a cached `SystemService` instance for dependency injection."""
    return SystemService()


@lru_cache
def get_upload_validator() -> UploadValidator:
    """Provide a cached `UploadValidator` instance for dependency injection.

    `UploadValidator` is stateless, so a single shared instance is reused
    across every request (ADR-011).
    """
    return UploadValidator()


@lru_cache
def get_prediction_service() -> PredictionService:
    """Provide a cached `PredictionService` instance for dependency injection.

    Phase 4.2 wired in the centralized `UploadValidator` (ADR-011). Phase
    4.5.4 wired in `RuntimeValidator` (ADR-015) and `RuntimeMetadataService`
    (ADR-016) so the RUNTIME pipeline stage executes for real. Phase 4.6.1
    wires in `ImagePreprocessor` (ADR-018) so the PREPROCESSING pipeline
    stage executes for real, ahead of the RUNTIME stage. Phase 4.6.2 wires
    in `PredictionRequestBuilder` (ADR-019) so the REQUEST_BUILDING
    pipeline stage executes for real, once PREPROCESSING and RUNTIME have
    both completed. Phase 4.6.3 wires in `PredictionEngine` (ADR-020) so
    the PREDICTION_ENGINE pipeline stage executes single-model inference
    for real, once REQUEST_BUILDING has completed. Phase 4.6.5 wires in
    `PredictionResultCollector` (ADR-022) so the RESULT_COLLECTION
    pipeline stage standardizes the Prediction Engine's output for real,
    once PREDICTION_ENGINE has completed. Phase 4.7.1 wires in
    `EnsembleEngine` (ADR-024) so the ENSEMBLE pipeline stage validates
    and prepares the standardized `PredictionExecutionResult` for real,
    once RESULT_COLLECTION has completed. Phase 4.7.4.2 wires in
    `AdaptiveWeightedVotingEngine` (ADR-025), `ConfidenceCalibrationEngine`
    (ADR-026), and `FinalPredictionBuilder` (ADR-027) so the internal
    FINAL_PREDICTION step runs for real, once ENSEMBLE has completed.
    Phase 4.8.2 wires in `PredictionResponseBuilder` (ADR-028) so the
    RESPONSE pipeline stage runs for real, once the internal
    FINAL_PREDICTION step has completed. Phase 5.2 wires in the HISTORY
    pipeline stage's persistence (ADR-033) -- but *not* through this
    provider: `PredictionHistoryService` is bound to a request-scoped
    database session (see `get_prediction_history_service` below), while
    this provider builds a process-wide, `lru_cache`d `PredictionService`
    singleton with no session of its own. Instead, the Prediction Router
    resolves a request-scoped `PredictionHistoryService` separately and
    passes it directly to `PredictionService.predict(history_service=...)`
    on each call.
    """
    return PredictionService(
        upload_validator=get_upload_validator(),
        image_preprocessor=get_image_preprocessor(),
        runtime_validator=get_runtime_validator(),
        runtime_metadata_service=get_runtime_metadata_service(),
        request_builder=get_prediction_request_builder(),
        prediction_engine=get_prediction_engine(
            runtime_manager=get_ai_runtime_manager(),
            registry=get_model_registry(),
        ),
        result_collector=get_prediction_result_collector(),
        ensemble_engine=get_prediction_ensemble_engine(),
        voting_engine=get_adaptive_weighted_voting_engine(registry=get_model_registry()),
        calibration_engine=get_confidence_calibration_engine(),
        final_prediction_builder=get_final_prediction_builder(),
        response_builder=get_prediction_response_builder(),
    )


@lru_cache
def get_prediction_request_builder() -> PredictionRequestBuilder:
    """Provide a cached `PredictionRequestBuilder` instance for dependency injection (ADR-019).

    `PredictionRequestBuilder` is stateless and has no external
    dependencies, so a single shared instance is reused across every
    request.
    """
    return PredictionRequestBuilder()


@lru_cache
def get_model_registry() -> ModelRegistry:
    """Provide a cached `ModelRegistry` loaded from the configured manifest.

    Cached so the manifest file is parsed and validated only once per
    process lifetime.
    """
    return ModelRegistry(load_manifest())


@lru_cache
def get_image_preprocessor() -> ImagePreprocessor:
    """Provide a cached `ImagePreprocessor` instance for dependency injection (ADR-018).

    Bound to the cached `ModelRegistry` so the preprocessing input size is
    sourced from the Model Manifest (ADR-006) rather than hardcoded;
    falls back to `Settings.DEFAULT_PREPROCESSING_INPUT_SIZE` only when no
    enabled model is currently registered. `ImagePreprocessor` never
    depends on `AIRuntimeManager`, so this provider stays independent from
    `get_ai_runtime_manager()`/`get_runtime_adapter()`.
    """
    return ImagePreprocessor(registry=get_model_registry())


@lru_cache
def get_model_cache_manager() -> ModelCacheManager:
    """Provide a cached `ModelCacheManager` instance for dependency injection."""
    return ModelCacheManager()


def get_huggingface_downloader(
    cache_manager: ModelCacheManager = Depends(get_model_cache_manager),
) -> HuggingFaceDownloader:
    """Provide a `HuggingFaceDownloader` bound to the shared cache manager."""
    return HuggingFaceDownloader(cache_manager)


def get_model_download_manager(
    registry: ModelRegistry = Depends(get_model_registry),
    cache_manager: ModelCacheManager = Depends(get_model_cache_manager),
    downloader: HuggingFaceDownloader = Depends(get_huggingface_downloader),
) -> ModelDownloadManager:
    """Provide a `ModelDownloadManager` wired with its dependencies.

    Not consumed by any endpoint in this phase; available for the Phase 3.2
    Model Manager to depend on.
    """
    return ModelDownloadManager(registry, cache_manager, downloader)


def get_model_metadata_service(
    registry: ModelRegistry = Depends(get_model_registry),
    cache_manager: ModelCacheManager = Depends(get_model_cache_manager),
) -> ModelMetadataService:
    """Provide a `ModelMetadataService` wired with its dependencies."""
    return ModelMetadataService(registry, cache_manager)


@lru_cache
def get_ai_runtime_manager() -> AIRuntimeManager:
    """Provide the process-wide `AIRuntimeManager` singleton for dependency injection.

    `AIRuntimeManager` enforces its own singleton identity (see ADR-007), so
    this provider is cached only to avoid rebuilding its constructor
    arguments on every call; the manager itself would return the same
    instance regardless.
    """
    registry = get_model_registry()
    cache_manager = get_model_cache_manager()
    downloader = HuggingFaceDownloader(cache_manager)
    download_manager = ModelDownloadManager(registry, cache_manager, downloader)
    return AIRuntimeManager(
        registry=registry,
        download_manager=download_manager,
        cache_manager=cache_manager,
    )


@lru_cache
def get_runtime_adapter() -> RuntimeAdapter:
    """Provide a cached `RuntimeAdapter` instance for dependency injection.

    Wraps the singleton `AIRuntimeManager` and cached `ModelRegistry`
    behind the metadata-only surface `PredictionService` is allowed to
    depend on (ADR-014). Cached for the same reason as
    `get_ai_runtime_manager`: to avoid rebuilding constructor arguments on
    every call.
    """
    return RuntimeAdapter(
        runtime_manager=get_ai_runtime_manager(),
        registry=get_model_registry(),
    )


@lru_cache
def get_runtime_validator() -> RuntimeValidator:
    """Provide a cached `RuntimeValidator` instance for dependency injection (ADR-015)."""
    return RuntimeValidator(runtime_adapter=get_runtime_adapter())


@lru_cache
def get_runtime_metadata_service() -> RuntimeMetadataService:
    """Provide a cached `RuntimeMetadataService` instance for dependency injection (ADR-016)."""
    return RuntimeMetadataService(runtime_adapter=get_runtime_adapter())


def get_prediction_engine(
    runtime_manager: AIRuntimeManager = Depends(get_ai_runtime_manager),
    registry: ModelRegistry = Depends(get_model_registry),
) -> PredictionEngine:
    """Provide a request-scoped `PredictionEngine` wired with its dependencies.

    Not consumed by any endpoint in this phase; available for the Phase 4
    Prediction APIs to depend on.
    """
    return PredictionEngine(runtime_manager=runtime_manager, registry=registry)


@lru_cache
def get_prediction_result_collector() -> PredictionResultCollector:
    """Provide a cached `PredictionResultCollector` instance for dependency injection (ADR-022).

    Bound to the cached `ModelRegistry` so skipped models (registered
    candidates never attempted for a given request) can be reported by ID;
    `PredictionResultCollector` never depends on `AIRuntimeManager`, so
    this provider stays independent from `get_ai_runtime_manager()`/
    `get_runtime_adapter()`, mirroring `get_image_preprocessor()`.
    """
    return PredictionResultCollector(registry=get_model_registry())


def get_ensemble_engine(
    registry: ModelRegistry = Depends(get_model_registry),
) -> AdaptiveEnsembleEngine:
    """Provide a request-scoped `AdaptiveEnsembleEngine` wired with its dependencies.

    Not consumed by any endpoint in this phase; available for future
    final-prediction phases (Phase 4.7.4 onward) to depend on.
    """
    return AdaptiveEnsembleEngine(registry=registry)


@lru_cache
def get_prediction_ensemble_engine() -> EnsembleEngine:
    """Provide a cached `EnsembleEngine` instance for dependency injection (ADR-024).

    `EnsembleEngine` is stateless and has no external dependencies -- it
    validates and prepares an `EnsembleRequest` without communicating
    with `AIRuntimeManager`, `ModelRegistry`, or the database -- so a
    single shared instance is reused across every request, consistent
    with `get_prediction_request_builder()`. Consumed by
    `get_prediction_service()` to connect the ENSEMBLE pipeline stage
    (Phase 4.7.1).
    """
    return EnsembleEngine()


def get_adaptive_weighted_voting_engine(
    registry: ModelRegistry = Depends(get_model_registry),
) -> AdaptiveWeightedVotingEngine:
    """Provide a request-scoped `AdaptiveWeightedVotingEngine` instance (ADR-025).

    Bound to the cached `ModelRegistry` so each participating model's
    manifest-configured `ensemble_weight` (ADR-006) is read from the
    Model Manifest rather than hardcoded; `AdaptiveWeightedVotingEngine`
    never depends on `AIRuntimeManager`, so this provider stays
    independent from `get_ai_runtime_manager()`/`get_runtime_adapter()`,
    mirroring `get_image_preprocessor()` and
    `get_prediction_result_collector()`. Consumed by
    `get_prediction_service()` to run the internal FINAL_PREDICTION step
    (Phase 4.7.4.2).
    """
    return AdaptiveWeightedVotingEngine(registry=registry)


@lru_cache
def get_confidence_calibration_engine() -> ConfidenceCalibrationEngine:
    """Provide a cached `ConfidenceCalibrationEngine` instance for dependency injection (ADR-026).

    `ConfidenceCalibrationEngine` is stateless and has no external
    dependencies -- every calculation it performs is a pure function of
    the `VotingResult` it is given -- so a single shared instance is
    reused across every request, consistent with
    `get_prediction_ensemble_engine()`. Consumed by
    `get_prediction_service()` to run the internal FINAL_PREDICTION step
    (Phase 4.7.4.2).
    """
    return ConfidenceCalibrationEngine()


@lru_cache
def get_final_prediction_builder() -> FinalPredictionBuilder:
    """Provide a cached `FinalPredictionBuilder` instance for dependency injection (ADR-027).

    `FinalPredictionBuilder` is stateless and has no external
    dependencies -- it only copies fields from the
    `CalibratedEnsembleResult` it is given -- so a single shared instance
    is reused across every request, consistent with
    `get_confidence_calibration_engine()`. Consumed by
    `get_prediction_service()` to run the internal FINAL_PREDICTION step
    (Phase 4.7.4.2).
    """
    return FinalPredictionBuilder()


@lru_cache
def get_prediction_response_builder() -> PredictionResponseBuilder:
    """Provide a cached `PredictionResponseBuilder` instance for dependency injection (ADR-028).

    `PredictionResponseBuilder` is stateless and has no external
    dependencies -- it only copies fields from the `FinalPredictionResult`
    it is given -- so a single shared instance is reused across every
    request, consistent with `get_final_prediction_builder()`. Consumed
    by `get_prediction_service()` to run the RESPONSE pipeline stage
    (Phase 4.8.2).
    """
    return PredictionResponseBuilder()


@lru_cache
def get_password_service() -> PasswordService:
    """Provide a cached `PasswordService` instance for dependency injection."""
    return PasswordService()


@lru_cache
def get_jwt_service() -> JWTService:
    """Provide a cached `JWTService` instance for dependency injection."""
    return JWTService()


def get_prediction_history_repository(
    session: AsyncSession = Depends(get_db),
) -> PredictionHistoryRepository:
    """Provide a request-scoped `PredictionHistoryRepository` bound to the current session.

    Returns a `SQLAlchemyPredictionHistoryRepository` (Phase 5.2, ADR-033).
    Not cached with `@lru_cache`, unlike most other providers in this
    module: `AsyncSession` is request-scoped (see `get_db`), so a fresh
    repository instance is required on every request, mirroring
    `get_user_repository` and `get_refresh_token_repository`.
    """
    return SQLAlchemyPredictionHistoryRepository(session)


def get_prediction_history_service(
    repository: PredictionHistoryRepository = Depends(get_prediction_history_repository),
) -> PredictionHistoryService:
    """Provide a request-scoped `PredictionHistoryService` wired with its repository (Phase 5.2, ADR-033).

    Not cached: depends transitively on the request-scoped `AsyncSession`
    through `get_prediction_history_repository`. Consumed directly by the
    Prediction Router, which passes the resulting instance to
    `PredictionService.predict(history_service=...)` -- `PredictionService`
    itself remains a cached, session-independent singleton (see
    `get_prediction_service`).
    """
    return PredictionHistoryService(repository=repository)


@lru_cache
def get_report_builder() -> ReportBuilder:
    """Provide a cached `ReportBuilder` instance for dependency injection (Phase 6.1, ADR-037).

    `ReportBuilder` is stateless and has no external dependencies -- it
    only aggregates fields already present on the `PredictionHistory`
    collection it is given -- so a single shared instance is reused
    across every request, consistent with `get_prediction_response_builder()`.
    """
    return ReportBuilder()


@lru_cache
def get_report_validator() -> ReportValidator:
    """Provide a cached `ReportValidator` instance for dependency injection (Phase 6.1, ADR-037).

    `ReportValidator` is stateless and has no external dependencies, so a
    single shared instance is reused across every request, consistent
    with `get_upload_validator()`.
    """
    return ReportValidator()


def get_report_service(
    history_repository: PredictionHistoryRepository = Depends(get_prediction_history_repository),
    builder: ReportBuilder = Depends(get_report_builder),
    validator: ReportValidator = Depends(get_report_validator),
) -> ReportService:
    """Provide a request-scoped `ReportService` wired with its dependencies (Phase 6.1, ADR-037).

    Not cached: depends transitively on the request-scoped `AsyncSession`
    through `get_prediction_history_repository`, mirroring
    `get_prediction_history_service`. Reuses `PredictionHistoryRepository`
    directly -- no separate reporting repository exists (ADR-037).
    """
    return ReportService(
        history_repository=history_repository,
        validator=validator,
        builder=builder,
    )


@lru_cache
def get_analytics_builder() -> AnalyticsBuilder:
    """Provide a cached `AnalyticsBuilder` instance for dependency injection (Phase 6.2, ADR-038).

    `AnalyticsBuilder` is stateless and has no external dependencies -- it
    only aggregates fields already present on the `PredictionHistory`
    collection it is given -- so a single shared instance is reused
    across every request, consistent with `get_report_builder()`.
    """
    return AnalyticsBuilder()


@lru_cache
def get_analytics_validator() -> AnalyticsValidator:
    """Provide a cached `AnalyticsValidator` instance for dependency injection (Phase 6.2, ADR-038).

    `AnalyticsValidator` is stateless and has no external dependencies, so
    a single shared instance is reused across every request, consistent
    with `get_report_validator()`.
    """
    return AnalyticsValidator()


def get_prediction_analytics_service(
    history_repository: PredictionHistoryRepository = Depends(get_prediction_history_repository),
    builder: AnalyticsBuilder = Depends(get_analytics_builder),
    validator: AnalyticsValidator = Depends(get_analytics_validator),
) -> PredictionAnalyticsService:
    """Provide a request-scoped `PredictionAnalyticsService` wired with its dependencies (Phase 6.2, ADR-038).

    Not cached: depends transitively on the request-scoped `AsyncSession`
    through `get_prediction_history_repository`, mirroring
    `get_report_service`. Reuses `PredictionHistoryRepository` directly --
    no separate analytics repository exists (ADR-038).
    """
    return PredictionAnalyticsService(
        history_repository=history_repository,
        validator=validator,
        builder=builder,
    )


@lru_cache
def get_csv_export_builder() -> CSVExportBuilder:
    """Provide a cached `CSVExportBuilder` instance for dependency injection (Phase 6.3, ADR-039).

    `CSVExportBuilder` is stateless and has no external dependencies -- it
    only serializes fields already present on the `PredictionHistory`
    collection and `PredictionAnalyticsResult` it is given -- so a single
    shared instance is reused across every request, consistent with
    `get_analytics_builder()`.
    """
    return CSVExportBuilder()


@lru_cache
def get_csv_validator() -> CSVValidator:
    """Provide a cached `CSVValidator` instance for dependency injection (Phase 6.3, ADR-039).

    `CSVValidator` is stateless and has no external dependencies, so a
    single shared instance is reused across every request, consistent
    with `get_analytics_validator()`.
    """
    return CSVValidator()


def get_csv_export_service(
    history_repository: PredictionHistoryRepository = Depends(get_prediction_history_repository),
    analytics_service: PredictionAnalyticsService = Depends(get_prediction_analytics_service),
    builder: CSVExportBuilder = Depends(get_csv_export_builder),
    validator: CSVValidator = Depends(get_csv_validator),
) -> CSVExportService:
    """Provide a request-scoped `CSVExportService` wired with its dependencies (Phase 6.3, ADR-039).

    Not cached: depends transitively on the request-scoped `AsyncSession`
    through `get_prediction_history_repository`, mirroring
    `get_prediction_analytics_service`. Reuses `PredictionHistoryRepository`
    and `PredictionAnalyticsService` directly -- no separate CSV export
    repository exists (ADR-039).
    """
    return CSVExportService(
        history_repository=history_repository,
        analytics_service=analytics_service,
        validator=validator,
        builder=builder,
    )


@lru_cache
def get_pdf_builder() -> PDFBuilder:
    """Provide a cached `PDFBuilder` instance for dependency injection (Phase 6.4, ADR-040).

    `PDFBuilder` is stateless and has no external dependencies -- it only
    renders fields already present on the `PredictionHistory` collection
    and `PredictionAnalyticsResult` it is given -- so a single shared
    instance is reused across every request, consistent with
    `get_csv_export_builder()`.
    """
    return PDFBuilder()


@lru_cache
def get_pdf_validator() -> PDFValidator:
    """Provide a cached `PDFValidator` instance for dependency injection (Phase 6.4, ADR-040).

    `PDFValidator` is stateless and has no external dependencies, so a
    single shared instance is reused across every request, consistent
    with `get_csv_validator()`.
    """
    return PDFValidator()


def get_pdf_export_service(
    history_repository: PredictionHistoryRepository = Depends(get_prediction_history_repository),
    analytics_service: PredictionAnalyticsService = Depends(get_prediction_analytics_service),
    builder: PDFBuilder = Depends(get_pdf_builder),
    validator: PDFValidator = Depends(get_pdf_validator),
) -> PDFExportService:
    """Provide a request-scoped `PDFExportService` wired with its dependencies (Phase 6.4, ADR-040).

    Not cached: depends transitively on the request-scoped `AsyncSession`
    through `get_prediction_history_repository`, mirroring
    `get_csv_export_service`. Reuses `PredictionHistoryRepository` and
    `PredictionAnalyticsService` directly -- no separate PDF export
    repository exists (ADR-040).
    """
    return PDFExportService(
        history_repository=history_repository,
        analytics_service=analytics_service,
        validator=validator,
        builder=builder,
    )


def get_user_repository(session: AsyncSession = Depends(get_db)) -> UserRepository:
    """Provide a request-scoped `UserRepository` bound to the current session."""
    return UserRepository(session)


def get_admin_user_service(
    session: AsyncSession = Depends(get_db),
    user_repository: UserRepository = Depends(get_user_repository),
) -> AdminUserService:
    """Provide a request-scoped `AdminUserService` wired with its dependencies (Phase 7.2/7.3).

    Not cached: depends transitively on the request-scoped `AsyncSession`,
    mirroring `get_auth_service`. Intentionally never wired with
    `PasswordService`/`JWTService` -- administrators must never be able to
    manipulate password hashes or tokens directly (ADR-036).
    """
    return AdminUserService(session=session, user_repository=user_repository)


def get_admin_history_service(
    history_service: PredictionHistoryService = Depends(get_prediction_history_service),
) -> AdminHistoryService:
    """Provide a request-scoped `AdminHistoryService` wired with its dependencies (Phase 7.4).

    Not cached: depends transitively on the request-scoped `AsyncSession`
    through `get_prediction_history_service`. Reuses `PredictionHistoryService`
    directly -- no separate admin history repository exists (ADR-036).
    """
    return AdminHistoryService(history_service=history_service)


@lru_cache
def get_admin_system_service() -> AdminSystemService:
    """Provide a cached `AdminSystemService` instance for dependency injection (Phase 7.5).

    Reuses the singleton `AIRuntimeManager` (see `get_ai_runtime_manager`)
    and the cached `SystemService` -- no second runtime manager is
    introduced (ADR-036).
    """
    return AdminSystemService(
        runtime_manager=get_ai_runtime_manager(),
        system_service=get_system_service(),
    )


@lru_cache
def get_monitoring_service() -> MonitoringService:
    """Provide a cached `MonitoringService` instance for dependency injection (Phase 8.1).

    Reuses the singleton `AIRuntimeManager` (see `get_ai_runtime_manager`)
    and the cached `SystemService` -- no second runtime manager is
    introduced (ADR-036).
    """
    return MonitoringService(
        runtime_manager=get_ai_runtime_manager(),
        system_service=get_system_service(),
        request_metrics_collector=default_request_metrics_collector,
    )


def get_refresh_token_repository(
    session: AsyncSession = Depends(get_db),
) -> RefreshTokenRepository:
    """Provide a request-scoped `RefreshTokenRepository` bound to the current session."""
    return RefreshTokenRepository(session)


def get_auth_service(
    session: AsyncSession = Depends(get_db),
    user_repository: UserRepository = Depends(get_user_repository),
    refresh_token_repository: RefreshTokenRepository = Depends(get_refresh_token_repository),
    password_service: PasswordService = Depends(get_password_service),
    jwt_service: JWTService = Depends(get_jwt_service),
) -> AuthService:
    """Provide a request-scoped `AuthService` wired with its dependencies."""
    return AuthService(
        session=session,
        user_repository=user_repository,
        refresh_token_repository=refresh_token_repository,
        password_service=password_service,
        jwt_service=jwt_service,
    )
