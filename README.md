# WisprClone
A fast, local-configurable voice-to-text Windows application using Groq API (Whisper + Llama3.1) to transcribe and correct your dictated text,, injecting it directly into your active window. Optional integration to categorize and send your notes to a Notion database!

## Features
- Global Hotkey for quick dictation.
- Transcription using Whisper-large-v3.
- Automatic text correction, punctuation inference, and filler-word removal using Llama-3.1-8b-instant.
- Prompt injection protection against stray dictation commands.
- **Notion Integration**: Optional categorization and synchronization of dictated thoughts straight into your Notion Database.
- Built-in UI to configure settings and keys safely.

## Setup Requirements
1. Python 3.10+
2. A free [Groq API Key](https://console.groq.com/keys).

### For Notion Integration (Optional)
To send notes to Notion, you need:
1. A Notion API Secret (create one at https://www.notion.so/my-integrations).
2. Connect your integration to the specific Notion Database.
3. The Notion Database should contain these properties:
   - **Name** (Title type)
   - **Topic** (Select type)
   - **Tags** (Multi-select type)
   - **Useful** (Checkbox type)
   - **Text** (Text / rich text type)

## How to Run from Source / Python
1. Clone the repository.
2. Install the necessary dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python main.py
   ```
   (Wait for the setup window. Note that if you're missing a Groq key the settings window will open automatically).

## How to Compile to a standalone `.exe` for Windows
You can build a portable Windows executable using PyInstaller. A build script is provided.
1. Make sure you have PyInstaller installed.
   ```bash
   pip install pyinstaller
   ```
2. Run the build script:
   ```bash
   python build.py
   ```
3. The compiled `.exe` will be located in the `dist` folder. You can distribute this single file safely.

## Configuration
All configuration variables (Hotkeys, API keys) are stored locally in `%appdata%\WisprClone\config.json`. Do not commit your personal keys to GitHub! You can also use `.env` if developing locally. See `.env.example`.
