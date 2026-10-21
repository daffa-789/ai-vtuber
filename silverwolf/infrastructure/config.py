"""Infrastructure: Global Configuration.

Re-exports configuration objects and functions for clean infrastructure layer access.
"""

from silverwolf.config import AppConfig, ROOT_DIR, config, resolve_path

__all__ = ["AppConfig", "ROOT_DIR", "config", "resolve_path"]
