import pystray
from PIL import Image, ImageDraw
import threading
import subprocess
import sys
import os
class TrayApp:
    def __init__(self, on_exit_callback):
        self.on_exit_callback = on_exit_callback
        self.icon = None
        self.running = False
        
    def _create_image(self, color):
        # Generate an image with a colored circle
        width = 64
        height = 64
        # Use transparent background
        image = Image.new('RGBA', (width, height), color=(255, 255, 255, 0))
        dc = ImageDraw.Draw(image)
        dc.ellipse((16, 16, 48, 48), fill=color)
        return image

    def start(self):
        self.running = True
        
        def run_tray():
            menu = pystray.Menu(
                pystray.MenuItem('Settings', self._on_settings),
                pystray.MenuItem('Exit', self._on_exit)
            )
            self.icon = pystray.Icon("WhisperApp", self._create_image("black"), "WisprClone (Voice-to-Text)", menu)
            self.icon.run()
            
        self.thread = threading.Thread(target=run_tray, daemon=True)
        self.thread.start()

    def set_recording(self, is_recording):
        """Changes the tray icon color based on recording state."""
        if self.icon:
            color = "red" if is_recording else "black"
            self.icon.icon = self._create_image(color)

    def stop(self):
        if self.icon:
            self.icon.stop()

    def _on_settings(self, icon, item):
        # Open Settings window as an independent process
        if getattr(sys, 'frozen', False):
            # PyInstaller bundle: sys.executable is the .exe itself
            subprocess.Popen([sys.executable, "--settings"])
        else:
            settings_script = os.path.join(os.path.dirname(__file__), "settings_ui.py")
            subprocess.Popen([sys.executable, settings_script])

    def _on_exit(self, icon, item):
        self.running = False
        self.icon.stop()
        self.on_exit_callback()
