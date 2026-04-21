import os
import json
import sys
from utils.logger import setup_logger, get_logger

logger = get_logger("yapclean.config")


class ConfigManager:
    """Manages reading and writing application configuration to APPDATA."""
    
    def __init__(self):
        self.app_name = "YapClean"
        self.app_dir = os.path.join(os.getenv("APPDATA", ""), self.app_name)
        self.config_path = os.path.join(self.app_dir, "config.json")
        self.settings = self._load_default_settings()
        self._ensure_dir_and_load()
        setup_logger(self.app_dir)
        self._migrate_secrets_to_keyring()

    def _load_default_settings(self):
        """Load default settings - only non-sensitive data."""
        return {
            "hotkey": "ctrl+alt+space",
            "autostart": False,
            "notion_database_id": "",
            "translate_to_layout": False,
            "dictation_language": "Russian",
            "enable_notion": True,
            "notion_trigger_word": "заметка",
            "ui_language": "en",
            "show_pill_overlay": True
        }

    def _ensure_dir_and_load(self):
        if not os.path.exists(self.app_dir):
            try:
                os.makedirs(self.app_dir)
            except Exception as e:
                logger.error(f"Error creating directory: {e}")
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.settings.update(data)
            except Exception as e:
                logger.error(f"Error loading config: {e}")
        else:
            self.save_settings()

    def _migrate_secrets_to_keyring(self):
        """Migrate API keys from config.json to keyring on first run after update."""
        from storage.keyring_manager import keyring_manager
        
        secret_keys = ["api_key", "deepgram_api_key", "notion_api_key", "openai_api_key"]
        migrated = False
        
        for key in secret_keys:
            if key in self.settings and self.settings[key]:
                # Migrate to keyring
                value = self.settings[key]
                existing = keyring_manager.get(key)
                if not existing:
                    keyring_manager.save(key, value)
                    logger.info(f"Migrated '{key}' to keyring.")
                # Remove from settings dict
                del self.settings[key]
                migrated = True
        
        if migrated:
            self.save_settings()

    def save_settings(self):
        if not os.path.exists(self.app_dir):
            os.makedirs(self.app_dir, exist_ok=True)
        
        # Ensure no secret keys are written to disk
        secret_keys = {"api_key", "deepgram_api_key", "notion_api_key", "openai_api_key"}
        safe_settings = {k: v for k, v in self.settings.items() if k not in secret_keys}
            
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(safe_settings, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving config: {e}")

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        # Silently refuse to store secret keys in config
        secret_keys = {"api_key", "deepgram_api_key", "notion_api_key", "openai_api_key"}
        if key in secret_keys:
            logger.warning(f"'{key}' is a secret — use KeyringManager instead.")
            return
        self.settings[key] = value
        self.save_settings()


config_manager = ConfigManager()
