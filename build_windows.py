"""
build_windows.py — Windows build script for YapClean
Produces: dist/YapClean/ (onedir) ready for NSIS packaging
Usage: python build_windows.py
"""
import PyInstaller.__main__
import os
import sys

# Ensure __init__.py exists at root (required for some import chains)
if not os.path.exists("__init__.py"):
    with open("__init__.py", "w") as f:
        f.write("")

# Remove stale spec
spec_file = "YapClean.spec"
if os.path.exists(spec_file):
    os.remove(spec_file)
    print(f"Removed old {spec_file}")

print("Building YapClean for Windows...")

import customtkinter
ctk_path = os.path.dirname(customtkinter.__file__)

# Collect i18n locale files
locales_src = os.path.join("i18n", "locales")

PyInstaller.__main__.run([
    "main.py",
    "--name=YapClean",
    "--noconsole",
    "--onedir",
    "--clean",
    "--noconfirm",
    "--noupx",
    # Data files
    f"--add-data={ctk_path}{os.pathsep}customtkinter/",
    f"--add-data={locales_src}{os.pathsep}i18n/locales/",
    # Hidden imports — all new modules added in Phase 1-3
    "--hidden-import=settings_ui",
    "--hidden-import=PIL",
    "--hidden-import=pystray",
    "--hidden-import=pynput",
    "--hidden-import=pynput.keyboard",
    "--hidden-import=pynput.mouse",
    "--hidden-import=keyring",
    "--hidden-import=keyring.backends",
    "--hidden-import=keyring.backends.Windows",
    "--hidden-import=keyring.backends.fail",
    "--hidden-import=watchdog",
    "--hidden-import=watchdog.observers",
    "--hidden-import=watchdog.events",
    "--hidden-import=psutil",
    "--hidden-import=plyer",
    "--hidden-import=plyer.platforms",
    "--hidden-import=plyer.platforms.win",
    "--hidden-import=plyer.platforms.win.notification",
    "--hidden-import=groq",
    "--hidden-import=openai",
    "--hidden-import=sounddevice",
    "--hidden-import=soundfile",
    "--hidden-import=customtkinter",
    # App modules
    "--hidden-import=storage.config_manager",
    "--hidden-import=storage.keyring_manager",
    "--hidden-import=core.pipeline",
    "--hidden-import=core.app_awareness",
    "--hidden-import=core.audio_manager",
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
    "--icon=NONE",
    # Exclude heavy ML libraries not needed at runtime
    "--exclude-module=torch",
    "--exclude-module=torchvision",
    "--exclude-module=torchaudio",
    "--exclude-module=scipy",
    "--exclude-module=sklearn",
    "--exclude-module=matplotlib",
    "--exclude-module=pandas",
    "--exclude-module=IPython",
    "--exclude-module=jupyter",
    "--exclude-module=notebook",
    "--exclude-module=jedi",
    "--exclude-module=pytest",
    "--exclude-module=hypothesis",
])

print("Build complete! Output: dist/YapClean/YapClean.exe")
print("Next step: run NSIS with installer.nsi to create the installer.")
