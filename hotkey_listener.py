from pynput import keyboard as pynput_kb
from config import get_hotkey
from storage.config_manager import config_manager
from utils.logger import get_logger

logger = get_logger("yapclean.hotkey")


# Maps string token → set of pynput keys that satisfy it
_MODIFIER_MAP = {
    "ctrl":       {pynput_kb.Key.ctrl_l, pynput_kb.Key.ctrl_r},
    "alt":        {pynput_kb.Key.alt_l, pynput_kb.Key.alt_r},
    "shift":      {pynput_kb.Key.shift_l, pynput_kb.Key.shift_r},
    "space":      {pynput_kb.Key.space},
    "caps lock":  {pynput_kb.Key.caps_lock},
    "caps_lock":  {pynput_kb.Key.caps_lock},
    "right ctrl": {pynput_kb.Key.ctrl_r},
    "right alt":  {pynput_kb.Key.alt_r},
    "right shift":{pynput_kb.Key.shift_r},
    "right cmd":  {pynput_kb.Key.cmd_r},
    "cmd":        {pynput_kb.Key.cmd_l, pynput_kb.Key.cmd_r},
    "ctrl+space": {pynput_kb.Key.ctrl_l, pynput_kb.Key.ctrl_r},  # parsed as combo
}

# Named function keys
for _i in range(1, 13):
    _MODIFIER_MAP[f"f{_i}"] = {getattr(pynput_kb.Key, f"f{_i}")}


def _parse_hotkey(hotkey_str: str):
    """
    Parse a hotkey string like 'ctrl+alt+space' into a list of key-sets.
    Each element is a set of pynput keys; pressing ANY key in the set counts
    as satisfying that slot (handles left/right variants).
    Returns list[set].
    """
    parts = [p.strip().lower() for p in hotkey_str.split("+")]
    result = []
    for part in parts:
        if part in _MODIFIER_MAP:
            result.append(_MODIFIER_MAP[part])
        else:
            # Treat as a regular character key
            result.append({pynput_kb.KeyCode.from_char(part)})
    return result


def _key_matches_slot(key, slot: set) -> bool:
    """Return True if *key* satisfies any member of *slot*."""
    if key in slot:
        return True
    # Also compare KeyCode by char (handles platform differences)
    if isinstance(key, pynput_kb.KeyCode):
        for s in slot:
            if isinstance(s, pynput_kb.KeyCode) and s.char == key.char:
                return True
    return False


class HotkeyListener:
    def __init__(self, on_press_cb, on_release_cb):
        self.on_press_cb = on_press_cb
        self.on_release_cb = on_release_cb
        self._is_recording = False
        self._running = False
        self._listener = None
        self._pressed = set()          # currently held pynput keys
        self._combo_active = False     # True while combo is considered "held"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_slots(self):
        return _parse_hotkey(get_hotkey())

    def _is_toggle_mode(self) -> bool:
        hotkey = get_hotkey().lower().strip()
        if hotkey in ("caps lock", "caps_lock"):
            return True
        return config_manager.get("hotkey_mode", "hold") == "toggle"

    def _all_slots_pressed(self) -> bool:
        slots = self._get_slots()
        for slot in slots:
            if not any(_key_matches_slot(k, slot) for k in self._pressed):
                return False
        return True

    def _any_slot_released(self, released_key) -> bool:
        """Return True if *released_key* belongs to any slot of the combo."""
        for slot in self._get_slots():
            if _key_matches_slot(released_key, slot):
                return True
        return False

    # ------------------------------------------------------------------
    # pynput callbacks
    # ------------------------------------------------------------------

    def _on_press(self, key):
        if not self._running:
            return False  # stop listener

        self._pressed.add(key)

        if self._is_toggle_mode():
            # Only fire on the exact moment the combo becomes fully pressed
            if self._all_slots_pressed() and not self._combo_active:
                self._combo_active = True
                if not self._is_recording:
                    self._is_recording = True
                    try:
                        self.on_press_cb()
                    except (KeyboardInterrupt, SystemExit):
                        raise
                    except Exception as e:
                        logger.error(f"Hotkey press callback failed: {e}", exc_info=True)
                        try:
                            from app_platform.notifications import notify
                            notify("YapClean", "Hotkey processing failed - check logs", "error")
                        except Exception:
                            pass
                else:
                    self._is_recording = False
                    try:
                        self.on_release_cb()
                    except (KeyboardInterrupt, SystemExit):
                        raise
                    except Exception as e:
                        logger.error(f"Hotkey release callback failed: {e}", exc_info=True)
                        try:
                            from app_platform.notifications import notify
                            notify("YapClean", "Hotkey processing failed - check logs", "error")
                        except Exception:
                            pass
        else:
            # Hold-to-talk: fire on_press_cb when all slots are pressed
            if self._all_slots_pressed() and not self._combo_active:
                self._combo_active = True
                self._is_recording = True
                try:
                    self.on_press_cb()
                except (KeyboardInterrupt, SystemExit):
                        raise
                except Exception as e:
                    logger.error(f"Hotkey press callback failed: {e}", exc_info=True)
                    try:
                        from app_platform.notifications import notify
                        notify("YapClean", "Hotkey processing failed - check logs", "error")
                    except Exception:
                        pass

    def _on_release(self, key):
        if not self._running:
            return False  # stop listener

        if self._is_toggle_mode():
            # Reset combo_active so next press can fire again
            if self._any_slot_released(key):
                self._combo_active = False
        else:
            # Hold-to-talk: fire on_release_cb when any combo key is released
            if self._combo_active and self._any_slot_released(key):
                self._combo_active = False
                if self._is_recording:
                    self._is_recording = False
                    try:
                        self.on_release_cb()
                    except (KeyboardInterrupt, SystemExit):
                        raise
                    except Exception as e:
                        logger.error(f"Hotkey release callback failed: {e}", exc_info=True)
                        try:
                            from app_platform.notifications import notify
                            notify("YapClean", "Hotkey processing failed - check logs", "error")
                        except Exception:
                            pass

        self._pressed.discard(key)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self):
        """Start listening. Blocks until stop() is called."""
        logger.info(f"Listening for: {get_hotkey()}")
        self._running = True
        self._listener = pynput_kb.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.start()
        self._listener.join()

    def stop(self):
        """Stop the listener."""
        self._running = False
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
