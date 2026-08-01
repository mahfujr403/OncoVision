"""User-related Pydantic schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import UserRole


class UserResponse(BaseModel):
    """Public representation of a user, safe to return in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str
    role: UserRole
    is_active: bool
    is_verified: bool
    avatar_url: str | None = Field(default=None)
    last_login: datetime | None = Field(default=None)
    created_at: datetime
