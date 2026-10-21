"""Infrastructure: Logging Configuration.

Provides structured and clean logging configuration for the HuoHuo application.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional


def configure_logging(level: int = logging.INFO, logger_name: Optional[str] = "huohuo") -> logging.Logger:
    """Configure and return the root or named logger for HuoHuo."""
    logger = logging.getLogger(logger_name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger


logger = configure_logging()
