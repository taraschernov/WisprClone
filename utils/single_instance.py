import os
import platform as _platform
import tempfile


class SingleInstance:
    """Cross-platform single-instance guard.

    Usage:
        _instance = SingleInstance()
        if not _instance.acquire():
            sys.exit(0)
        try:
            run_app()
        finally:
            _instance.release()
    """

    def __init__(self):
        self._mutex = None
        self._pid_file = os.path.join(tempfile.gettempdir(), "yapclean.pid")

    def acquire(self) -> bool:
        """Returns True if this is the only instance, False if another is running."""
        if _platform.system() == "Windows":
            return self._acquire_windows()
        else:
            return self._acquire_unix()

    def release(self):
        """Release the lock/mutex acquired by this instance."""
        if _platform.system() == "Windows":
            self._release_windows()
        else:
            self._release_unix()

    # ------------------------------------------------------------------
    # Windows: named mutex via kernel32
    # ------------------------------------------------------------------

    def _acquire_windows(self) -> bool:
        import ctypes
        self._mutex = ctypes.windll.kernel32.CreateMutexW(
            None, False, "Global\\YapCleanSingleInstance"
        )
        ERROR_ALREADY_EXISTS = 183
        last_error = ctypes.windll.kernel32.GetLastError()
        return last_error != ERROR_ALREADY_EXISTS

    def _release_windows(self):
        if self._mutex:
            import ctypes
            ctypes.windll.kernel32.CloseHandle(self._mutex)
            self._mutex = None

    # ------------------------------------------------------------------
    # Unix (macOS / Linux): PID lock-file
    # ------------------------------------------------------------------

    def _acquire_unix(self) -> bool:
        if os.path.exists(self._pid_file):
            try:
                with open(self._pid_file, "r") as f:
                    old_pid = int(f.read().strip())
                os.kill(old_pid, 0)  # signal 0 — just checks if process is alive
                return False  # process is alive → already running
            except (ProcessLookupError, ValueError, OSError):
                pass  # stale file or invalid PID → safe to overwrite

        with open(self._pid_file, "w") as f:
            f.write(str(os.getpid()))
        return True

    def _release_unix(self):
        try:
            if os.path.exists(self._pid_file):
                os.remove(self._pid_file)
        except OSError:
            pass
