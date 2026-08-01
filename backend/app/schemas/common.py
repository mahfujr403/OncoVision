"""Common, reusable Pydantic schemas shared across endpoints."""

from pydantic import BaseModel, ConfigDict, Field


class HealthStatus(BaseModel):
    """Schema for the health check endpoint payload."""

    model_config = ConfigDict(json_schema_extra={"example": {"status": "healthy"}})

    status: str = Field(default="healthy", description="Current service health status.")


class StoragePaths(BaseModel):
    """Schema describing configured storage directory paths."""

    upload_path: str = Field(description="Directory used for uploaded images.")
    report_path: str = Field(description="Directory used for generated PDF reports.")
    model_storage_path: str = Field(description="Directory used for ML model artifacts.")


class ApplicationInfo(BaseModel):
    """Schema describing core application metadata."""

    name: str = Field(description="Application name.")
    version: str = Field(description="Application version.")
    environment: str = Field(description="Current runtime environment.")
    health_endpoint: str = Field(description="Relative URL of the health check endpoint.")


class SystemInfo(BaseModel):
    """Schema describing runtime system information."""

    application_name: str = Field(description="Application name.")
    version: str = Field(description="Application version.")
    environment: str = Field(description="Current runtime environment.")
    python_version: str = Field(description="Python interpreter version.")
    platform: str = Field(description="Operating system platform descriptor.")
    current_time: str = Field(description="Current server time in ISO 8601 format.")
    storage: StoragePaths = Field(description="Configured storage directory paths.")
