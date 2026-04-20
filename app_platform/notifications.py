import platform


def notify(title: str, message: str, level: str = "info") -> None:
    os_name = platform.system()
    try:
        if os_name == "Windows":
            _windows_notify(title, message)
        elif os_name == "Darwin":
            _macos_notify(title, message)
        elif os_name == "Linux":
            _linux_notify(title, message)
    except Exception:
        pass  # Notifications are non-critical


def _windows_notify(title, message):
    from plyer import notification
    notification.notify(title=title, message=message, app_name="YapClean", timeout=5)


def _macos_notify(title, message):
    import subprocess
    subprocess.run(["osascript", "-e",
                    f'display notification "{message}" with title "{title}"'],
                   capture_output=True)


def _linux_notify(title, message):
    import subprocess
    subprocess.run(["notify-send", title, message], capture_output=True)
