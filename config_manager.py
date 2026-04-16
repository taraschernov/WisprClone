import os
import json
import sys

class ConfigManager:
    """Manages reading and writing application configuration to APPDATA."""
    
    def __init__(self):
        self.app_name = "WisprClone"
        self.app_dir = os.path.join(os.getenv("APPDATA", ""), self.app_name)
        self.config_path = os.path.join(self.app_dir, "config.json")
        self.settings = self._load_default_settings()
        self._ensure_dir_and_load()

    def _load_default_settings(self):
        return {
            "api_key": "",
            "hotkey": "ctrl+alt+space",
            "autostart": False,
            "notion_api_key": "",
            "notion_database_id": "",
            "translate_to_layout": True,
            "enable_notion": True,
            "notion_trigger_word": "заметка"
        }

    def _ensure_dir_and_load(self):
        if not os.path.exists(self.app_dir):
            try:
                os.makedirs(self.app_dir)
            except Exception as e:
                print(f"[Config] Error creating directory: {e}")
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.settings.update(data)
            except Exception as e:
                print(f"[Config] Error loading config: {e}")
        else:
            self.save_settings()

    def save_settings(self):
        if not os.path.exists(self.app_dir):
            os.makedirs(self.app_dir, exist_ok=True)
            
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"[Config] Error saving config: {e}")

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value
        self.save_settings()

config_manager = ConfigManager()
