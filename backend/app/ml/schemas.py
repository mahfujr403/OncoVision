"""Schemas describing the model manifest and model registry API payloads.

`ModelManifestEntry` is the single source of truth for a model's metadata.
No model paths, weights, labels, or preprocessing settings may be
hardcoded outside of the manifest this schema validates.
"""

import re

from pydantic import BaseModel, Field, field_validator, model_validator


class ModelManifestEntry(BaseModel):
    """Metadata describing a single registered ML model."""

    id: str = Field(min_length=1, description="Unique identifier for the model.")
    display_name: str = Field(min_length=1, description="Human-readable model name.")
    version: str = Field(min_length=1, description="Model version identifier.")
    framework: str = Field(
        min_length=1,
        description="ML framework used to train and serve the model (e.g. 'tensorflow').",
    )
    format: str = Field(min_length=1, description="Serialized model file format (e.g. 'h5').")
    repository: str = Field(
        min_length=1, description="Hugging Face Hub repository ID hosting the model file."
    )
    filename: str = Field(
        min_length=1, description="Model weight filename within the repository and local cache."
    )
    priority: int = Field(gt=0, description="Loading priority; lower values load first.")
    ensemble_weight: float = Field(
        gt=0, le=1, description="Default weight assigned to this model in the ensemble."
    )
    input_size: int = Field(gt=0, description="Required square input image dimension, in pixels.")
    num_classes: int = Field(gt=0, description="Number of output classes the model predicts.")
    class_labels: list[str] = Field(
        min_length=1, description="Ordered class labels corresponding to model output indices."
    )
    sha256: str = Field(
        min_length=64,
        max_length=64,
        description="Expected SHA-256 checksum of the model weight file.",
    )
    enabled: bool = Field(default=True, description="Whether this model is enabled for use.")
    description: str = Field(min_length=1, description="Short description of the model.")

    @field_validator("class_labels")
    @classmethod
    def validate_class_labels_not_empty(cls, value: list[str]) -> list[str]:
        """Ensure no class label is a blank or whitespace-only string."""
        if any(not label.strip() for label in value):
            raise ValueError("class_labels must not contain empty values.")
        return value

    @field_validator("sha256")
    @classmethod
    def validate_sha256_format(cls, value: str) -> str:
        """Ensure the checksum is a well-formed 64-character hex string."""
        if not re.fullmatch(r"[0-9a-fA-F]{64}", value):
            raise ValueError("sha256 must be a 64-character hexadecimal string.")
        return value.lower()

    @model_validator(mode="after")
    def validate_class_label_count(self) -> "ModelManifestEntry":
        """Ensure `class_labels` has exactly `num_classes` entries."""
        if len(self.class_labels) != self.num_classes:
            raise ValueError(
                f"class_labels length ({len(self.class_labels)}) must match "
                f"num_classes ({self.num_classes})."
            )
        return self


class ModelManifest(BaseModel):
    """Root schema for the model manifest file."""

    manifest_version: str = Field(
        min_length=1, description="Version identifier of the manifest schema/content."
    )
    models: list[ModelManifestEntry] = Field(
        default_factory=list, description="All registered models."
    )


class ModelSummary(BaseModel):
    """Public summary of a registered model, safe to return via the API."""

    id: str = Field(description="Unique identifier for the model.")
    display_name: str = Field(description="Human-readable model name.")
    version: str = Field(description="Model version identifier.")
    framework: str = Field(description="ML framework used to train and serve the model.")
    format: str = Field(description="Serialized model file format.")
    priority: int = Field(description="Loading priority; lower values load first.")
    ensemble_weight: float = Field(description="Default weight assigned to this model in the ensemble.")
    input_size: int = Field(description="Required square input image dimension, in pixels.")
    num_classes: int = Field(description="Number of output classes the model predicts.")
    class_labels: list[str] = Field(description="Ordered class labels corresponding to model output indices.")
    enabled: bool = Field(description="Whether this model is enabled for use.")
    is_cached: bool = Field(description="Whether the model weight file is present in the local cache.")
    description: str = Field(description="Short description of the model.")


class ModelRegistryResponse(BaseModel):
    """Response payload summarizing the entire model registry."""

    manifest_version: str = Field(description="Version identifier of the loaded manifest.")
    total_models: int = Field(description="Total number of registered models.")
    enabled_models: int = Field(description="Number of models enabled for use.")
    disabled_models: int = Field(description="Number of models disabled in the manifest.")
    available_models: int = Field(
        description="Number of enabled models whose weight files are currently cached locally."
    )
    models: list[ModelSummary] = Field(description="Summary of every registered model.")
