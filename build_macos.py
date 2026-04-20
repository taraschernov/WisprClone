"""
build_macos.py — macOS build script for YapClean
Produces: dist/YapClean.app (then packaged into .dmg)
Usage: python build_macos.py
Requires: macOS, Xcode CLI tools, create-dmg (brew install create-dmg)
"""
import PyInstaller.__main__
import os
import subprocess
import sys

APP_NAME = "YapClean"
APP_VERSION = "1.0.0"
BUNDLE_ID = "tech.yapclean"

print(f"Building {APP_NAME} for macOS...")

import customtkinter
ctk_path = os.path.dirname(customtkinter.__file__)
locales_src = os.path.join("i18n", "locales")

PyInstaller.__main__.run([
    "main.py",
    f"--name={APP_NAME}",
    "--windowed",          # .app bundle, no terminal window
    "--onedir",
    "--clean",
    "--noconfirm",
    f"--add-data={ctk_path}:customtkinter/",
    f"--add-data={locales_src}:i18n/locales/",
    "--hidden-import=pynput",
    "--hidden-import=pynput.keyboard",
    "--hidden-import=keyring",
    "--hidden-import=keyring.backends",
    "--hidden-import=keyring.backends.macOS",
    "--hidden-import=watchdog",
    "--hidden-import=watchdog.observers",
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

# Inject Info.plist with required permissions
app_bundle = f"dist/{APP_NAME}.app"
info_plist_path = os.path.join(app_bundle, "Contents", "Info.plist")

if os.path.exists(info_plist_path):
    with open(info_plist_path, "r") as f:
        plist = f.read()

    # Insert permission keys before </dict>
    permissions = """
    <key>NSMicrophoneUsageDescription</key>
    <string>YapClean needs microphone access to record your voice for transcription.</string>
    <key>NSAccessibilityUsageDescription</key>
    <string>YapClean needs accessibility access to detect the active application for auto persona switching.</string>
    <key>CFBundleIdentifier</key>
    <string>tech.yapclean</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
"""
    plist = plist.replace("</dict>\n</plist>", permissions + "</dict>\n</plist>")
    with open(info_plist_path, "w") as f:
        f.write(plist)
    print("Info.plist updated with permissions.")

print(f"App bundle: {app_bundle}")
print("Next steps:")
print("  1. Code sign: codesign --deep --force --sign 'Developer ID Application: ...' dist/YapClean.app")
print("  2. Create DMG: create-dmg --volname YapClean --app-drop-link 450 200 dist/YapClean.dmg dist/YapClean.app")
print("  3. Notarize: xcrun notarytool submit dist/YapClean.dmg --apple-id ... --team-id ... --password ...")
