"""Structured logging configuration for the application.

Configures console logging and daily-rotating file logging, with separate
log files for INFO, WARNING, and ERROR levels. All application modules
should retrieve loggers via `get_logger(__name__)` to inherit this
configuration.
"""

import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from app.core.settings import get_settings

LOG_DIRECTORY = Path("logs")
LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s | "
    "%(filename)s:%(lineno)d | %(message)s"
)
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_CONFIGURED = False


class _LevelFilter(logging.Filter):
    """Filter that only allows records matching an exact log level."""

    def __init__(self, level: int) -> None:
        super().__init__()
        self._level = level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno == self._level


def _build_rotating_handler(filename: str, level: int) -> TimedRotatingFileHandler:
    """Create a daily-rotating file handler scoped to a single log level."""
    handler = TimedRotatingFileHandler(
        filename=LOG_DIRECTORY / filename,
        when="midnight",
        backupCount=30,
        encoding="utf-8",
        utc=True,
    )
    handler.setLevel(level)
    handler.addFilter(_LevelFilter(level))
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    return handler


def configure_logging() -> None:
    """Configure the root logger with console and rotating file handlers.

    Safe to call multiple times; configuration is only applied once per
    process.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    settings = get_settings()
    LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)
    root_logger.handlers.clear()

    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setLevel(settings.LOG_LEVEL)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    root_logger.addHandler(console_handler)

    root_logger.addHandler(_build_rotating_handler("info.log", logging.INFO))
    root_logger.addHandler(_build_rotating_handler("warning.log", logging.WARNING))
    root_logger.addHandler(_build_rotating_handler("error.log", logging.ERROR))

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger for the given module name.

    Args:
        name: Typically `__name__` of the calling module.
    """
    if not _CONFIGURED:
        configure_logging()
    return logging.getLogger(name)
