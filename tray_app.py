import pystray
from PIL import Image, ImageDraw
import threading
import subprocess
import sys
import os
from i18n.translator import t
from storage.config_manager import config_manager
from utils.logger import get_logger

logger = get_logger("yapclean.tray")

PERSONAS = [
    "General User",
    "IT Specialist / Developer",
    "Manager / Entrepreneur",
    "Writer / Blogger / Marketer",
    "Medical / Legal / Researcher",
    "Support Specialist",
    "HR / Recruiter",
    "Teacher / Trainer",
]

# Icon colors per state
_COLORS = {
    "idle": "black",
    "recording": "red",
    "processing": "#FFA500",  # orange
    "error": "#8B0000",       # dark red
}


class TrayApp:
    def __init__(self, on_exit_callback):
        self.on_exit_callback = on_exit_callback
        self.icon = None
        self.running = False
        self._state = "idle"

    def _create_image(self, color):
        width = 64
        height = 64
        image = Image.new("RGBA", (width, height), color=(255, 255, 255, 0))
        dc = ImageDraw.Draw(image)
        dc.ellipse((16, 16, 48, 48), fill=color)
        return image

    def _build_menu(self):
        """Build tray context menu with persona submenu."""
        active_persona = config_manager.get("active_persona", "General User")

        def make_persona_callback(persona):
            def callback(icon, item):
                config_manager.set("active_persona", persona)
                logger.info(f"Persona switched to: {persona}")
                # Rebuild menu to update checkmark
                self.icon.menu = self._build_menu()
            return callback

        persona_items = [
            pystray.MenuItem(
                persona,
                make_persona_callback(persona),
                checked=lambda item, p=persona: config_manager.get("active_persona", "General User") == p,
                radio=True,
            )
            for persona in PERSONAS
        ]

        return pystray.Menu(
            pystray.MenuItem(
                t("tray.persona"),
                pystray.Menu(*persona_items),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(t("tray.settings"), self._on_settings),
            pystray.MenuItem(t("tray.exit"), self._on_exit),
        )

    def start(self):
        self.running = True

        def run_tray():
            self.icon = pystray.Icon(
                "YapClean",
                self._create_image(_COLORS["idle"]),
                t("tray.idle"),
                self._build_menu(),
            )
            self.icon.run()

        self.thread = threading.Thread(target=run_tray, daemon=True)
        self.thread.start()

    def set_state(self, state: str):
        """Set tray icon state: idle | recording | processing | error"""
        self._state = state
        if self.icon:
            color = _COLORS.get(state, "black")
            self.icon.icon = self._create_image(color)
            tooltip = {
                "idle": t("tray.idle"),
                "recording": t("tray.recording"),
                "processing": t("tray.processing"),
            }.get(state, t("tray.idle"))
            self.icon.title = tooltip

    def set_recording(self, is_recording: bool):
        """Convenience wrapper — kept for backward compatibility."""
        self.set_state("recording" if is_recording else "idle")

    def set_processing(self, is_processing: bool):
        """Set processing (yellow) state."""
        self.set_state("processing" if is_processing else "idle")

    def stop(self):
        if self.icon:
            self.icon.stop()

    def _on_settings(self, icon, item):
        if getattr(sys, "frozen", False):
            subprocess.Popen([sys.executable, "--settings"])
        else:
            settings_script = os.path.join(os.path.dirname(__file__), "ui", "settings_webview.py")
            subprocess.Popen([sys.executable, settings_script])

    def _on_exit(self, icon, item):
        self.running = False
        self.icon.stop()
        self.on_exit_callback()
