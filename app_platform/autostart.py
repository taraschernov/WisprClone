import platform
import sys
import os

APP_NAME = "YapClean"


def enable_autostart() -> None:
    os_name = platform.system()
    exe_path = sys.executable if getattr(sys, 'frozen', False) else f'"{sys.executable}" "{os.path.abspath("main.py")}"'
    if os_name == "Windows":
        _windows_enable(exe_path)
    elif os_name == "Darwin":
        _macos_enable(exe_path)
    elif os_name == "Linux":
        _linux_enable(exe_path)


def disable_autostart() -> None:
    os_name = platform.system()
    if os_name == "Windows":
        _windows_disable()
    elif os_name == "Darwin":
        _macos_disable()
    elif os_name == "Linux":
        _linux_disable()


def _windows_enable(exe_path):
    import winreg
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                         r"Software\Microsoft\Windows\CurrentVersion\Run",
                         0, winreg.KEY_ALL_ACCESS)
    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
    winreg.CloseKey(key)


def _windows_disable():
    import winreg
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run",
                             0, winreg.KEY_ALL_ACCESS)
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
    except FileNotFoundError:
        pass


def _macos_enable(exe_path):
    plist_path = os.path.expanduser("~/Library/LaunchAgents/tech.yapclean.plist")
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>tech.yapclean</string>
    <key>ProgramArguments</key>
    <array><string>{exe_path}</string></array>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><false/>
</dict>
</plist>"""
    os.makedirs(os.path.dirname(plist_path), exist_ok=True)
    with open(plist_path, "w") as f:
        f.write(plist_content)


def _macos_disable():
    plist_path = os.path.expanduser("~/Library/LaunchAgents/tech.yapclean.plist")
    if os.path.exists(plist_path):
        os.remove(plist_path)


def _linux_enable(exe_path):
    service_dir = os.path.expanduser("~/.config/systemd/user")
    os.makedirs(service_dir, exist_ok=True)
    service_path = os.path.join(service_dir, "yapclean.service")
    service_content = f"""[Unit]
Description=YapClean Voice Input
After=graphical-session.target

[Service]
ExecStart={exe_path}
Restart=on-failure

[Install]
WantedBy=default.target
"""
    with open(service_path, "w") as f:
        f.write(service_content)
    import subprocess
    subprocess.run(["systemctl", "--user", "enable", "yapclean.service"],
                   capture_output=True)


def _linux_disable():
    import subprocess
    subprocess.run(["systemctl", "--user", "disable", "yapclean.service"],
                   capture_output=True)
    service_path = os.path.expanduser("~/.config/systemd/user/yapclean.service")
    if os.path.exists(service_path):
        os.remove(service_path)
