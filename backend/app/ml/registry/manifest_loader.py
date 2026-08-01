"""Loads and validates the model manifest file.

The manifest is the single source of truth for model metadata. This module
performs two layers of validation: Pydantic schema validation (types,
required fields, per-field constraints) and cross-entry integrity checks
(unique IDs, unique priorities, unique filenames).
"""

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.core.settings import get_settings
from app.ml.exceptions import ModelManifestError
from app.ml.schemas import ModelManifest


def load_manifest_file(path: Path) -> dict[str, Any]:
    """Read and JSON-decode the manifest file at `path`.

    Raises:
        ModelManifestError: If the file does not exist or is not valid JSON.
    """
    if not path.is_file():
        raise ModelManifestError(f"Model manifest file not found at '{path}'.")

    try:
        with path.open("r", encoding="utf-8") as manifest_file:
            return json.load(manifest_file)
    except json.JSONDecodeError as exc:
        raise ModelManifestError(f"Model manifest file is not valid JSON: {exc}") from exc


def parse_manifest(raw_manifest: dict[str, Any]) -> ModelManifest:
    """Validate raw manifest data against the `ModelManifest` schema.

    Raises:
        ModelManifestError: If the manifest fails schema validation.
    """
    try:
        return ModelManifest.model_validate(raw_manifest)
    except ValidationError as exc:
        raise ModelManifestError(
            message="Model manifest failed schema validation.",
            errors=exc.errors(include_url=False, include_context=False),
        ) from exc


def validate_manifest_integrity(manifest: ModelManifest) -> None:
    """Validate cross-entry integrity rules that Pydantic cannot express alone.

    Checks for duplicate model IDs, duplicate loading priorities, and
    duplicate filenames across all registered models.

    Raises:
        ModelManifestError: If any integrity rule is violated.
    """
    ids = [model.id for model in manifest.models]
    if len(ids) != len(set(ids)):
        duplicates = sorted({model_id for model_id in ids if ids.count(model_id) > 1})
        raise ModelManifestError(f"Duplicate model IDs found in manifest: {duplicates}")

    priorities = [model.priority for model in manifest.models]
    if len(priorities) != len(set(priorities)):
        duplicates = sorted({priority for priority in priorities if priorities.count(priority) > 1})
        raise ModelManifestError(f"Duplicate model priorities found in manifest: {duplicates}")

    filenames = [model.filename for model in manifest.models]
    if len(filenames) != len(set(filenames)):
        duplicates = sorted({name for name in filenames if filenames.count(name) > 1})
        raise ModelManifestError(f"Duplicate model filenames found in manifest: {duplicates}")


def load_manifest(path: Path | None = None) -> ModelManifest:
    """Load, parse, and validate the model manifest.

    Args:
        path: Optional override path to the manifest file. Defaults to the
            configured `MODEL_MANIFEST_PATH` setting.

    Returns:
        A fully validated `ModelManifest`.
    """
    manifest_path = path or Path(get_settings().MODEL_MANIFEST_PATH)
    raw_manifest = load_manifest_file(manifest_path)
    manifest = parse_manifest(raw_manifest)
    validate_manifest_integrity(manifest)
    return manifest
