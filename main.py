import sys
import os
import threading
import time
from audio_manager import AudioManager
from clipboard_injector import ClipboardInjector
from hotkey_listener import HotkeyListener
from tray_app import TrayApp
from config_manager import config_manager
from storage.keyring_manager import keyring_manager
from core.pipeline import Pipeline
from core.app_awareness import AppAwarenessManager
from personas.router import PersonaRouter
from utils.logger import get_logger
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess
import ctypes

logger = get_logger("yapclean.app")


class _ConfigChangeHandler(FileSystemEventHandler):
    def __init__(self, app):
        self._app = app
        self._last_reload = 0

    def on_modified(self, event):
        now = time.time()
        if now - self._last_reload < 0.5:
            return
        self._last_reload = now
        if not event.is_directory:
            self._app.reload_config()


class App:
    def __init__(self):
        self.audio = AudioManager()
        self.injector = ClipboardInjector()
        self._app_awareness = AppAwarenessManager()
        self._persona_router = PersonaRouter()
        self.pipeline = Pipeline(self.injector, self._app_awareness, self._persona_router)
        self.hotkey = HotkeyListener(self.on_hotkey_press, self.on_hotkey_release)
        self.tray = TrayApp(self.on_exit)
        self.running = True
        self.current_language = None
        self._observer = None

    def get_current_keyboard_language(self):
        try:
            user32 = ctypes.WinDLL('user32', use_last_error=True)
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return None
            thread_id = user32.GetWindowThreadProcessId(hwnd, 0)
            layout_id = user32.GetKeyboardLayout(thread_id)
            language_id = layout_id & 0xFFFF
            langs = {
                0x0409: "English",
                0x0809: "English (UK)",
                0x0419: "Russian",
                0x0422: "Ukrainian",
                0x0407: "German",
                0x040C: "French",
                0x040A: "Spanish",
            }
            return langs.get(language_id, f"Language ID: {hex(language_id)}")
        except Exception as e:
            logger.error(f"Error getting layout: {e}")
            return None

    def on_hotkey_press(self):
        logger.info("Hotkey pressed. Starting recording...")
        dictation_lang = config_manager.get("dictation_language", "Russian")
        translate = config_manager.get("translate_to_layout", False)

        if translate:
            self.current_language = self.get_current_keyboard_language()
            logger.info(f"Translate mode: detected layout → {self.current_language}")
        else:
            self.current_language = dictation_lang
            logger.info(f"Dictation language: {self.current_language}")
            
        self.tray.set_recording(True)
        self.audio.start_recording()

    def on_hotkey_release(self):
        import time
        start_time = time.time()
        logger.info("Hotkey released. Processing audio...")
        self.tray.set_recording(False)
        audio_filepath = self.audio.stop_recording()
        
        target_lang = self.current_language
        
        if audio_filepath:
            def process():
                self.tray.set_processing(True)
                try:
                    self.pipeline.process(audio_filepath, target_language=target_lang)
                    total_time = time.time() - start_time
                    logger.info(f"---> Total time from dictation to clipboard: {total_time:.2f} seconds")
                finally:
                    self.tray.set_processing(False)
            threading.Thread(target=process, daemon=True).start()

    def on_exit(self):
        logger.info("Exiting...")
        self.running = False
        if self._observer is not None:
            self._observer.stop()
            self._observer.join()
        self.hotkey.stop()
        self.tray.stop()

    def reload_config(self):
        """Reload config from disk when config.json changes (triggered by watchdog)."""
        try:
            import json
            with open(config_manager.config_path, "r", encoding="utf-8") as f:
                new_settings = json.load(f)
            
            # Reload all settings that can change at runtime (non-secret only)
            runtime_keys = [
                "translate_to_layout", "dictation_language",
                "notion_database_id", "enable_notion", "notion_trigger_word",
                "current_mode", "presets", "custom_system_prompt"
            ]
            for key in runtime_keys:
                new_val = new_settings.get(key)
                if new_val != config_manager.get(key):
                    config_manager.settings[key] = new_val

            # Restart hotkey listener if hotkey changed
            new_hotkey = new_settings.get("hotkey")
            if new_hotkey and new_hotkey != config_manager.get("hotkey"):
                config_manager.settings["hotkey"] = new_hotkey
                self.hotkey.stop()
                self.hotkey_thread.join()
                self.hotkey = HotkeyListener(self.on_hotkey_press, self.on_hotkey_release)
                self.hotkey_thread = threading.Thread(target=self.hotkey.start, daemon=True)
                self.hotkey_thread.start()
        except Exception:
            pass

    def start_config_watcher(self):
        """Start a watchdog observer to watch config.json for changes."""
        config_dir = os.path.dirname(config_manager.config_path)
        handler = _ConfigChangeHandler(self)
        self._observer = Observer()
        self._observer.schedule(handler, path=config_dir, recursive=False)
        self._observer.start()
        logger.info(f"Config watcher started on: {config_dir}")

    def run(self):
        # Run onboarding wizard on first launch
        if not config_manager.get("onboarding_complete", False):
            from ui.onboarding import run_onboarding
            run_onboarding()

        self.tray.start()
        self.hotkey_thread = threading.Thread(target=self.hotkey.start, daemon=True)
        self.hotkey_thread.start()
        self.start_config_watcher()
        
        logger.info("Application is running.")
        logger.info("Press the hotkey (check settings) to speak.")
        
        try:
            while self.running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt. Exiting...")
        finally:
            self.on_exit()
        
        sys.exit(0)

if __name__ == "__main__":
    from utils.single_instance import SingleInstance

    _instance = SingleInstance()
    if not _instance.acquire():
        logger.info("[App] Already running. Exiting.")
        sys.exit(0)

    try:
        if "--settings" in sys.argv:
            from settings_ui import open_settings
            open_settings()
        else:
            app = App()
            try:
                app.run()
            except KeyboardInterrupt:
                pass
            finally:
                app.on_exit()
    finally:
        _instance.release()

