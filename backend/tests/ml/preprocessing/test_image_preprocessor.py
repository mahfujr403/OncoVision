"""Verification tests for the Phase 4.6.1 Image Preprocessing pipeline (ADR-018).

Uses a real `ModelRegistry` built from an in-memory `ModelManifest` (no
Hugging Face download, no TensorFlow) so these tests exercise
`ImagePreprocessor`'s own resolution and transform logic in isolation,
following the same fixture pattern used in
`tests/services/test_runtime_adapter.py`.

Not wired into a CI runner in this phase; run standalone with:
    PYTHONPATH=. python3 tests/ml/preprocessing/test_image_preprocessor.py
"""

import io

import numpy as np
from PIL import Image

from app.core.settings import Settings
from app.ml.preprocessing.exceptions import UnreadableImageError
from app.ml.preprocessing.image_preprocessor import ImagePreprocessor
from app.ml.preprocessing.preprocessing_result import DEFAULT_SOURCE, MANIFEST_SOURCE
from app.ml.registry.model_registry import ModelRegistry
from app.ml.schemas import ModelManifest, ModelManifestEntry

CLASS_LABELS = ["lung_n", "lung_scc", "lung_aca"]


def _manifest_entry(model_id: str, priority: int, input_size: int, enabled: bool = True) -> ModelManifestEntry:
    return ModelManifestEntry(
        id=model_id,
        display_name=model_id.replace("_", " ").title(),
        version="1.0.0",
        framework="tensorflow",
        format="h5",
        repository="oncovision-ai/models",
        filename=f"{model_id}.h5",
        priority=priority,
        ensemble_weight=0.5,
        input_size=input_size,
        num_classes=len(CLASS_LABELS),
        class_labels=CLASS_LABELS,
        sha256="a" * 64,
        enabled=enabled,
        description=f"Test manifest entry for {model_id}.",
    )


def make_registry(entries: list[ModelManifestEntry]) -> ModelRegistry:
    return ModelRegistry(ModelManifest(manifest_version="test-manifest-v1", models=entries))


def make_image_bytes(fmt: str, size: tuple[int, int] = (96, 64), mode: str = "RGB") -> bytes:
    buffer = io.BytesIO()
    Image.new(mode, size, color=(10, 90, 140) if mode == "RGB" else 128).save(buffer, format=fmt)
    return buffer.getvalue()


def check(name: str, condition: bool) -> bool:
    print(f"[{'PASS' if condition else 'FAIL'}] {name}")
    return condition


def run_case(name: str, func, expect_exception=None) -> bool:
    try:
        result = func()
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


def main() -> None:
    results: list[bool] = []

    registry = make_registry(
        [
            _manifest_entry("mobilenet_v2", priority=1, input_size=128),
            _manifest_entry("densenet_121", priority=2, input_size=256),
        ]
    )
    preprocessor = ImagePreprocessor(registry=registry)

    # 1. JPEG preprocessing end-to-end.
    jpeg_result = preprocessor.preprocess(make_image_bytes("JPEG"))
    results.append(check(
        "JPEG preprocessing succeeds and reports the source format",
        jpeg_result.preprocessing_success and jpeg_result.image_format == "JPEG",
    ))

    # 2. PNG preprocessing end-to-end.
    png_result = preprocessor.preprocess(make_image_bytes("PNG"))
    results.append(check(
        "PNG preprocessing succeeds and reports the source format",
        png_result.preprocessing_success and png_result.image_format == "PNG",
    ))

    # 3. TIFF preprocessing end-to-end.
    tiff_result = preprocessor.preprocess(make_image_bytes("TIFF"))
    results.append(check(
        "TIFF preprocessing succeeds and reports the source format",
        tiff_result.preprocessing_success and tiff_result.image_format == "TIFF",
    ))

    # 4. Manifest-driven input size: the lowest-priority (priority=1) enabled
    #    model's input_size (128) is used, never hardcoded.
    results.append(check(
        "Preprocessing resolves input size from the Model Manifest (priority=1 model)",
        jpeg_result.processed_width == 128
        and jpeg_result.processed_height == 128
        and jpeg_result.input_size == 128
        and jpeg_result.preprocessing_source == MANIFEST_SOURCE,
    ))

    # 5. RGB conversion: a grayscale ("L" mode) source is converted before resizing.
    grayscale_result = preprocessor.preprocess(make_image_bytes("PNG", mode="L"))
    results.append(check(
        "Grayscale source image is converted to RGB before inference",
        grayscale_result.processed_tensor.shape[-1] == 3,
    ))

    # 6. Resize: original dimensions differ from the manifest-driven processed dimensions.
    results.append(check(
        "Original dimensions are preserved separately from processed (resized) dimensions",
        jpeg_result.original_width == 96
        and jpeg_result.original_height == 64
        and jpeg_result.processed_width == 128
        and jpeg_result.processed_height == 128,
    ))

    # 7. Normalization: pixel values remain raw [0, 255] float32, matching
    #    what every current production model was trained on (no
    #    Rescaling(1./255) was ever applied during training).
    tensor = jpeg_result.processed_tensor
    results.append(check(
        "Processed tensor values fall within [0, 255] and use float32",
        tensor.dtype == np.float32 and float(tensor.min()) >= 0.0 and float(tensor.max()) <= 255.0,
    ))

    # 8. Batch dimension: shape is (1, H, W, 3).
    results.append(check(
        "Processed tensor has a leading batch dimension of size 1",
        tensor.shape == (1, 128, 128, 3),
    ))

    # 9. Default configuration fallback when no registry is available.
    no_registry_preprocessor = ImagePreprocessor(registry=None, settings=Settings())
    default_result = no_registry_preprocessor.preprocess(make_image_bytes("JPEG"))
    results.append(check(
        "Falls back to the centralized default input size when no registry is injected",
        default_result.input_size == Settings().DEFAULT_PREPROCESSING_INPUT_SIZE
        and default_result.preprocessing_source == DEFAULT_SOURCE,
    ))

    # 10. Default configuration fallback when the registry has zero enabled models.
    disabled_registry = make_registry(
        [_manifest_entry("mobilenet_v2", priority=1, input_size=128, enabled=False)]
    )
    disabled_preprocessor = ImagePreprocessor(registry=disabled_registry)
    disabled_result = disabled_preprocessor.preprocess(make_image_bytes("JPEG"))
    results.append(check(
        "Falls back to the centralized default input size when zero models are enabled",
        disabled_result.preprocessing_source == DEFAULT_SOURCE,
    ))

    # 11. PreprocessingResult serialization excluding the raw tensor.
    serialized = jpeg_result.model_dump(exclude={"processed_tensor"})
    results.append(check(
        "PreprocessingResult serializes cleanly excluding the raw tensor",
        isinstance(serialized, dict)
        and "processed_tensor" not in serialized
        and serialized["preprocessing_success"] is True,
    ))

    # 12. Unreadable image data raises UnreadableImageError and never reaches later stages.
    results.append(run_case(
        "Corrupted/unreadable image bytes raise UnreadableImageError",
        lambda: preprocessor.preprocess(b"not-a-real-image"),
        expect_exception=UnreadableImageError,
    ))

    # 13. preprocessing_time_ms is recorded and non-negative.
    results.append(check(
        "preprocessing_time_ms is recorded as a non-negative float",
        isinstance(jpeg_result.preprocessing_time_ms, float) and jpeg_result.preprocessing_time_ms >= 0,
    ))

    total = len(results)
    passed = sum(1 for r in results if r)
    print(f"\n{passed}/{total} checks passed.")
    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
