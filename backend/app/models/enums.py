"""Enumerations shared by ORM models and Pydantic schemas."""

from enum import Enum


class UserRole(str, Enum):
    """Application user roles.

    New roles can be added here without changing any authorization logic
    that depends on `require_roles`.
    """

    ADMIN = "admin"
    USER = "user"
