import time
import keyboard
import pyperclip

class ClipboardInjector:
    def inject_text(self, text):
        """Pastes text directly to the active window by automating Ctrl+V."""
        if not text:
            return
            
        print("[Injector] Preparing to inject text...")
        
        # Backup clipboard
        old_clipboard = pyperclip.paste()
        try:
            # Copy new text
            pyperclip.copy(text)
            
            # Allow time for clipboard to catch up
            time.sleep(0.05)
            
            # Send Ctrl+V
            keyboard.send("ctrl+v")
            
            # Wait for application to process paste
            time.sleep(0.15)
        except Exception as e:
            print(f"[Injector] Error injecting text: {e}")
        finally:
            # Restore clipboard
            pyperclip.copy(old_clipboard)
            print("[Injector] Text injected and clipboard restored.")
