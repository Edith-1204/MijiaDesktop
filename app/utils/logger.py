"""Safe application logging configuration."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from app.utils.paths import log_directory


LOGGER_NAME = "mijia_desktop"


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure console and rotating-file logging once per process."""
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    logger.propagate = False
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    try:
        directory = log_directory()
        directory.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            directory / "mijia-desktop.log",
            maxBytes=2 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        logger.warning("File logging is unavailable", exc_info=True)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Return a child logger without exposing credentials in configuration."""
    return logging.getLogger(f"{LOGGER_NAME}.{name}")

