# Backward-compatibility shim — imports from storage package
from storage.config_manager import ConfigManager, config_manager

__all__ = ["ConfigManager", "config_manager"]
