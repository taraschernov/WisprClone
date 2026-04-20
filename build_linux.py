"""
build_linux.py — Linux build script for YapClean
Produces: dist/YapClean/ (onedir), then packaged into AppImage or .deb
Usage: python build_linux.py
"""
import PyInstaller.__main__
import os

APP_NAME = "YapClean"

print(f"Building {APP_NAME} for Linux...")

import customtkinter
ctk_path = os.path.dirname(customtkinter.__file__)
locales_src = os.path.join("i18n", "locales")

PyInstaller.__main__.run([
    "main.py",
    f"--name={APP_NAME}",
    "--noconsole",
    "--onedir",
    "--clean",
    "--noconfirm",
    f"--add-data={ctk_path}:customtkinter/",
    f"--add-data={locales_src}:i18n/locales/",
    "--hidden-import=pynput",
    "--hidden-import=pynput.keyboard",
    "--hidden-import=keyring",
    "--hidden-import=keyring.backends",
    "--hidden-import=keyring.backends.SecretService",
    "--hidden-import=keyring.backends.fail",
    "--hidden-import=watchdog",
    "--hidden-import=watchdog.observers",
    "--hidden-import=watchdog.observers.inotify",
    "--hidden-import=psutil",
    "--hidden-import=plyer",
    "--hidden-import=groq",
    "--hidden-import=openai",
    "--hidden-import=sounddevice",
    "--hidden-import=soundfile",
    "--hidden-import=customtkinter",
    "--hidden-import=storage.config_manager",
    "--hidden-import=storage.keyring_manager",
    "--hidden-import=core.pipeline",
    "--hidden-import=core.app_awareness",
    "--hidden-import=providers.registry",
    "--hidden-import=providers.base",
    "--hidden-import=providers.stt.groq_stt",
    "--hidden-import=providers.stt.deepgram_stt",
    "--hidden-import=providers.stt.openai_stt",
    "--hidden-import=providers.stt.local_whisper",
    "--hidden-import=providers.llm.groq_llm",
    "--hidden-import=providers.llm.openai_llm",
    "--hidden-import=providers.llm.ollama_llm",
    "--hidden-import=personas.prompts",
    "--hidden-import=personas.router",
    "--hidden-import=personas.refusal_detector",
    "--hidden-import=personas.stt_hints",
    "--hidden-import=integrations.notion",
    "--hidden-import=app_platform.autostart",
    "--hidden-import=app_platform.notifications",
    "--hidden-import=i18n.translator",
    "--hidden-import=utils.logger",
    "--hidden-import=utils.single_instance",
    "--hidden-import=ui.onboarding",
])

print(f"Build complete! Output: dist/{APP_NAME}/")
print("Next steps:")
print("  AppImage: ./package_appimage.sh")
print("  .deb:     ./package_deb.sh")
