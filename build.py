import PyInstaller.__main__
import os

# Create an empty __init__.py if missing (sometimes required for import chains)
if not os.path.exists("__init__.py"):
    with open("__init__.py", "w") as f:
        f.write("")

print("Building WisprClone...")

# Package into a single executable without a console window
# Using customtkinter requires adding its data folder
import customtkinter
ctk_path = os.path.dirname(customtkinter.__file__)

PyInstaller.__main__.run([
    'main.py',
    '--name=WisprClone',
    '--noconsole',
    '--onedir',
    f'--add-data={ctk_path};customtkinter/',
    '--clean',
    '--noconfirm',
    '--hidden-import=settings_ui',
    '--hidden-import=PIL',
    '--hidden-import=pystray',
    '--icon=NONE' # We don't have an .ico yet, fallback to default
])

print("Build complete! Check the 'dist' folder for WisprClone.exe.")
