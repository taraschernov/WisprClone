from storage.config_manager import config_manager
from utils.logger import get_logger

logger = get_logger("yapclean.router")

DEFAULT_APP_BINDINGS = {
    "code": "IT Specialist / Developer",
    "cursor": "IT Specialist / Developer",
    "idea64": "IT Specialist / Developer",
    "pycharm64": "IT Specialist / Developer",
    "pycharm": "IT Specialist / Developer",
    "webstorm64": "IT Specialist / Developer",
    "slack": "General User",
    "telegram": "General User",
    "discord": "General User",
    "winword": "Manager / Entrepreneur",
    "notion": "Manager / Entrepreneur",
    "chrome": "General User",
    "firefox": "General User",
    "msedge": "General User",
    # Terminals — developer context
    "powershell": "IT Specialist / Developer",
    "windowsterminal": "IT Specialist / Developer",
    "cmd": "IT Specialist / Developer",
    "wt": "IT Specialist / Developer",
    "alacritty": "IT Specialist / Developer",
    "wezterm": "IT Specialist / Developer",
}


class PersonaRouter:
    def resolve(self, process_name: str) -> str:
        """Returns persona name for the given process. Falls back to config default."""
        if not process_name:
            return self._default()
        key = process_name.lower().replace(".exe", "").strip()
        # User-defined bindings override defaults
        user_bindings = config_manager.get("app_bindings", {})
        if key in user_bindings:
            persona = user_bindings[key]
            logger.info(f"App-Awareness: '{key}' → '{persona}' (user binding)")
            return persona
        if key in DEFAULT_APP_BINDINGS:
            persona = DEFAULT_APP_BINDINGS[key]
            logger.info(f"App-Awareness: '{key}' → '{persona}' (default binding)")
            return persona
        return self._default()

    def _default(self) -> str:
        return config_manager.get("active_persona", "General User")
