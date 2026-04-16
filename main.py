import sys
import threading
import time
from audio_manager import AudioManager
from api_manager import APIManager
from clipboard_injector import ClipboardInjector
from hotkey_listener import HotkeyListener
from tray_app import TrayApp
from config_manager import config_manager
import subprocess

class App:
    def __init__(self):
        self.audio = AudioManager()
        self.api = APIManager()
        self.injector = ClipboardInjector()
        self.hotkey = HotkeyListener(self.on_hotkey_press, self.on_hotkey_release)
        self.tray = TrayApp(self.on_exit)
        self.running = True

    def on_hotkey_press(self):
        print("[App] Hotkey pressed. Starting recording...")
        self.tray.set_recording(True)
        self.audio.start_recording()

    def on_hotkey_release(self):
        print("[App] Hotkey released. Processing audio...")
        self.tray.set_recording(False)
        audio_filepath = self.audio.stop_recording()
        
        if audio_filepath:
            def process():
                text = self.api.process_audio(audio_filepath)
                if text:
                    self.injector.inject_text(text)
                    # Trigger Notion upload in a background thread so it doesn't block
                    threading.Thread(target=self.api.categorize_and_send_to_notion, args=(text,), daemon=True).start()
                else:
                    print("[App] No text returned.")
            # Run processing in background so hotkey thread isn't blocked
            threading.Thread(target=process, daemon=True).start()

    def on_exit(self):
        print("[App] Exiting...")
        self.running = False
        self.hotkey.stop()
        self.tray.stop()

    def check_config_reload(self):
        """Periodically checks if the config file was modified and updates the App."""
        try:
            # Re-read config from disk to catch settings_ui updates
            import json
            with open(config_manager.config_path, "r", encoding="utf-8") as f:
                new_settings = json.load(f)
            
            # Check if API key changed
            if new_settings.get("api_key") != config_manager.get("api_key"):
                config_manager.set("api_key", new_settings.get("api_key"))
                self.api.client.api_key = config_manager.get("api_key")
                
            # Check if Hotkey changed
            new_hotkey = new_settings.get("hotkey")
            if new_hotkey != config_manager.get("hotkey"):
                config_manager.set("hotkey", new_hotkey)
                # Restart hotkey listener
                self.hotkey.stop()
                self.hotkey_thread.join()
                self.hotkey = HotkeyListener(self.on_hotkey_press, self.on_hotkey_release)
                self.hotkey_thread = threading.Thread(target=self.hotkey.start, daemon=True)
                self.hotkey_thread.start()
        except:
            pass

    def run(self):
        # Open Settings automatically if no API Key is provided
        if not config_manager.get("api_key"):
            self.tray._on_settings(None, None)
            
        self.tray.start()
        self.hotkey_thread = threading.Thread(target=self.hotkey.start, daemon=True)
        self.hotkey_thread.start()
        
        print("[App] Application is running.")
        print("[App] Press the hotkey (check settings) to speak.")
        
        try:
            counter = 0
            while self.running:
                time.sleep(0.5)
                counter += 1
                if counter % 4 == 0:  # Check for settings updates every 2 seconds
                    self.check_config_reload()
        except KeyboardInterrupt:
            print("[App] Keyboard interrupt. Exiting...")
        finally:
            self.on_exit()
        
        sys.exit(0)

if __name__ == "__main__":
    if "--settings" in sys.argv:
        from settings_ui import open_settings
        open_settings()
    else:
        app = App()
        app.run()
