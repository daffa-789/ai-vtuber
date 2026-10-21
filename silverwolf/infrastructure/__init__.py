"""Silver Wolf Infrastructure Layer.

Contains global configuration, logging, process lifecycle management,
and the Composition Root (Dependency Injection Container).
"""

from silverwolf.infrastructure.config import AppConfig, ROOT_DIR, config, resolve_path
from silverwolf.infrastructure.container import Container, create_container
from silverwolf.infrastructure.logging import configure_logging, logger

__all__ = [
    "AppConfig",
    "Container",
    "ROOT_DIR",
    "config",
    "configure_logging",
    "create_container",
    "logger",
    "resolve_path",
]
