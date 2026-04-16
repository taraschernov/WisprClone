# WisprClone
A fast, privacy-conscious voice-to-text Windows application. Hold a hotkey, speak — your text is instantly injected into the active window. Powered by Deepgram Nova-3 for ultra-fast transcription and optionally Groq Llama-3.1 for translation. Supports automatic categorization and sync to Notion.

## Features

### Core
- ⚡ **Ultra-fast transcription** — ~1.5–3 seconds from speech to clipboard using [Deepgram Nova-3](https://deepgram.com)
- 🎙️ **Global hotkey** — hold to record, release to inject. No window focus required
- 🔇 **Silence detection** — ignores empty recordings automatically
- 📋 **Clipboard-safe injection** — restores your original clipboard content after injecting text
- 🔒 **Prompt injection protection** — LLM ignores any commands spoken in audio

### Language & Translation
- 🌍 **Fixed dictation language** — choose your speaking language once in Settings (Russian, English, Ukrainian, etc.)
- 🔄 **Auto-translate mode** — optionally enable "translate to active keyboard layout" to dictate in one language and get output in another (uses Groq Llama-3.1; adds ~10s)

### Notion Integration (Optional)
- 📝 **Voice notes to Notion** — automatically categorize and sync your dictated thoughts to a Notion database
- 🔑 **Trigger word filter** — only notes that contain a specific word (e.g. "заметка") are sent to Notion; the trigger word is silently stripped from the final text
- 🏷️ **AI Categorization** — Llama-3.1 assigns Topic, Tags, and a Useful flag to each note
- 🔘 **Global on/off toggle** — enable or disable Notion sync without removing your API keys

### Settings UI
- Groq API Key (for Llama translation & Notion categorization)
- **Deepgram API Key** (for fast transcription — [get $200 free](https://deepgram.com))
- Dictation Language selector
- Translate-to-layout toggle
- Hotkey selector (6 presets)
- Notion API Key, Database ID, Trigger Word
- Windows Autostart toggle

---

## Setup

### Requirements
- Windows 10/11
- Python 3.10+
- A free [Groq API Key](https://console.groq.com/keys) (required for translation/Notion features)
- A free [Deepgram API Key](https://console.deepgram.com) — $200 free credit, enough for years of daily use (recommended for fastest transcription)

### Run from Source
```bash
git clone https://github.com/taraschernov/WisprClone.git
cd WisprClone
pip install -r requirements.txt
python main.py
```
The settings window opens automatically on first run if no API key is configured.

### For Notion Integration (Optional)
1. Create a Notion integration at https://www.notion.so/my-integrations and copy the **Internal Integration Secret**
2. Share your target database with the integration
3. The database must have these properties:
   - **Name** (Title)
   - **Topic** (Select)
   - **Tags** (Multi-select)
   - **Useful** (Checkbox)
   - **Text** (Rich text)

You can auto-create this schema using the included setup script:
```bash
python setup_notion_db.py
```

---

## Build Standalone `.exe`
```bash
pip install pyinstaller
python build.py
```
The portable executable will appear in the `dist/` folder.

---

## Configuration
All keys and settings are stored in `%APPDATA%\WisprClone\config.json` — never committed to git.
For local development, copy `.env.example` to `.env` and fill in your keys.
