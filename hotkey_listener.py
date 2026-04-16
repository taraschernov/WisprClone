import keyboard
import time
import threading
from config import get_hotkey

class HotkeyListener:
    def __init__(self, on_press, on_release):
        self.on_press = on_press
        self.on_release = on_release
        self.is_recording = False
        self.running = True
        self.thread = None

    def start(self):
        """Starts a background thread to monitor the hotkey state."""
        print(f"[Hotkey] Listening for: {get_hotkey()}")
        
        def loop():
            while self.running:
                # keyboard.is_pressed handles combinations like 'alt+space'
                try:
                    if keyboard.is_pressed(get_hotkey()):
                        if not self.is_recording:
                            self.is_recording = True
                            self.on_press()
                    else:
                        if self.is_recording:
                            self.is_recording = False
                            self.on_release()
                except Exception as e:
                    # Ignore errors like keyboard input hooked
                    pass
                time.sleep(0.05)
                
        self.thread = threading.Thread(target=loop, daemon=True)
        self.thread.start()
        
    def stop(self):
        """Stops the hotkey listener."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
