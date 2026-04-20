import PyInstaller.__main__
import os

# Create an empty __init__.py if missing (sometimes required for import chains)
if not os.path.exists("__init__.py"):
    with open("__init__.py", "w") as f:
        f.write("")

# Remove stale .spec to force regeneration from current flags
spec_file = "YapClean.spec"
if os.path.exists(spec_file):
    os.remove(spec_file)
    print(f"Removed old {spec_file}")

print("Building YapClean...")

# Package into a single executable without a console window
# Using customtkinter requires adding its data folder
import customtkinter
ctk_path = os.path.dirname(customtkinter.__file__)

PyInstaller.__main__.run([
    'main.py',
    '--name=YapClean',
    '--noconsole',
    '--onedir',
    f'--add-data={ctk_path};customtkinter/',
    '--clean',
    '--noconfirm',
    '--noupx',                          # Disable UPX — was corrupting the PKG archive
    '--hidden-import=settings_ui',
    '--hidden-import=PIL',
    '--hidden-import=pystray',
    '--icon=NONE',                      # No .ico yet, use default
])

print("Build complete! Run dist/YapClean/YapClean.exe")
