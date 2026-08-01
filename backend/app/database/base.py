"""Declarative base class for all SQLAlchemy ORM models.

All models must inherit from `Base` so that they are registered on a single
`MetaData` instance, which Alembic autogenerate relies on to detect schema
changes.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all application ORM models."""
