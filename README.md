# WisprClone
A fast, privacy-conscious voice-to-text Windows application. Hold a hotkey, speak — your text is instantly injected into the active window. Powered by Deepgram Nova-3 for ultra-fast transcription and optionally Groq Llama-3.1 for translation/correction. 

## Features

### Core
- ⚡ **Ultra-fast transcription** — ~1.5–3 seconds from speech to clipboard using [Deepgram Nova-3](https://deepgram.com)
- 🎙️ **Global hotkey** — hold to record, release to inject. No window focus required
- 🔇 **Silence detection** — ignores accidental clicks/silence automatically
- 📋 **Clipboard-safe** — automatically restores your original clipboard after injection
- 🔒 **Single Instance** — prevents multiple app icons in the tray
- 🔒 **Prompt injection protection** — AI ignores spoken commands in your dictation

### Language & Translation
- 🌍 **Fixed dictation language** — set your spoken language (Russian, English, etc.) once in settings
- 🔄 **Auto-translate mode** — toggle "translate to active layout" to dictate in one language and get text in another (uses Groq Llama-3.1)

### Notion Integration (Optional)
- 📝 **Voice notes to Notion** — categorize and sync thoughts to a Notion database
- 🔑 **Trigger word filter** — only sync notes containing a specific word (e.g. "заметка")
- 🏷️ **AI Categorization** — Llama-3.1 extracts Topic, Tags, and usefulness from your speech

### Modern Settings UI
- **Scrollable Interface** — fits all screen resolutions
- Hotkey presets (ctrl+alt, ctrl+shift, alt+shift, F8, F9, right ctrl)
- Windows Autostart toggle

---

## Setup

### Requirements
- Windows 10/11
- Python 3.10+
- [Groq API Key](https://console.groq.com/keys) (Free — for translation/Notion)
- [Deepgram API Key](https://console.deepgram.com) (Free — for ultra-fast STT)

### Run from Source
```bash
git clone https://github.com/taraschernov/WisprClone.git
cd WisprClone
pip install -r requirements.txt
python main.py
```

---

## Troubleshooting
- **Settings window cut off?** The new UI is scrollable! Use your mouse wheel to reach the "Save" button.
- **Translation not working?** 
  1. Ensure your Groq API key is valid.
  2. Click "Save" in settings after enabling the checkbox.
  3. Change your system keyboard layout (Alt+Shift/Win+Space) before speaking.
- **Notion notes failing?** Use `python setup_notion_db.py` to create the correct database schema automatically.
