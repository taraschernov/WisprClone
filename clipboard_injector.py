import time
import platform
import pyperclip
from utils.logger import get_logger

logger = get_logger("yapclean.injector")


def _send_paste_windows():
    """Send Ctrl+V on Windows using ctypes (most reliable method)."""
    import ctypes
    # Virtual key codes
    VK_CONTROL = 0x11
    VK_V = 0x56
    KEYEVENTF_KEYUP = 0x0002

    ctypes.windll.user32.keybd_event(VK_CONTROL, 0, 0, 0)
    time.sleep(0.02)
    ctypes.windll.user32.keybd_event(VK_V, 0, 0, 0)
    time.sleep(0.02)
    ctypes.windll.user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.02)
    ctypes.windll.user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)


def _send_paste_pynput():
    """Fallback: send Ctrl+V via pynput."""
    from pynput.keyboard import Controller, Key
    kb = Controller()
    with kb.pressed(Key.ctrl):
        kb.press('v')
        kb.release('v')


class ClipboardInjector:
    def inject_text(self, text):
        """Inject text into active window via clipboard."""
        if not text:
            return
        
        logger.info("Preparing to inject text...")
        try:
            # Do NOT save old clipboard - privacy risk
            pyperclip.copy(text)
            time.sleep(0.1)
            
            if platform.system() == "Windows":
                _send_paste_windows()
            else:
                _send_paste_pynput()
            
            time.sleep(0.15)
            logger.info("Text injected successfully.")
            
            # Clear clipboard after a delay to prevent accidental reuse
            # But do it only after sufficient delay
            time.sleep(2)
            pyperclip.copy("")  # Clear instead of restore
            
        except Exception as e:
            logger.error(f"Error injecting text: {e}")
            raise
