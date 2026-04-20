import platform
from utils.logger import get_logger

logger = get_logger("yapclean.app_awareness")


class AppAwarenessManager:
    def get_active_process(self) -> str:
        """Returns lowercase process name (without .exe) of the foreground window."""
        os_name = platform.system()
        try:
            if os_name == "Windows":
                return self._windows_get_process()
            elif os_name == "Darwin":
                return self._macos_get_process()
            elif os_name == "Linux":
                return self._linux_get_process()
        except Exception as e:
            logger.warning(f"App-Awareness failed: {e}")
        return ""

    def _windows_get_process(self) -> str:
        import ctypes
        import psutil
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return ""
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        name = psutil.Process(pid.value).name()
        return name.lower().replace(".exe", "")

    def _macos_get_process(self) -> str:
        import subprocess
        result = subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to get name of first process whose frontmost is true'],
            capture_output=True, text=True, timeout=2
        )
        return result.stdout.strip().lower()

    def _linux_get_process(self) -> str:
        import subprocess
        import psutil
        win_id = subprocess.run(
            ["xdotool", "getactivewindow"],
            capture_output=True, text=True, timeout=2
        ).stdout.strip()
        if not win_id:
            return ""
        pid_str = subprocess.run(
            ["xdotool", "getwindowpid", win_id],
            capture_output=True, text=True, timeout=2
        ).stdout.strip()
        if not pid_str:
            return ""
        return psutil.Process(int(pid_str)).name().lower()
