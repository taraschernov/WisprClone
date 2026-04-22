# YapClean — AI Voice Input

> Voice input, cleaned by AI. Speak — get polished text instantly in any app.
> 
> **Domain:** [yapclean.tech](https://yapclean.tech)

YapClean is a desktop voice dictation utility that transcribes your speech and formats it through an AI layer before inserting into the active window. It supports multiple user personas, auto-switches profiles by active app, and can translate on-the-fly based on your keyboard layout.

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/taraschernov/WisprClone.git
cd WisprClone
pip install -r requirements.txt
```

### 2. Set up your API key

Open `setup_keys.py`, paste your Groq API key, and run:

```bash
python setup_keys.py
```

Get a free Groq key at [console.groq.com](https://console.groq.com) — takes 30 seconds, no credit card.

### 3. Run

```bash
python main.py
```

On first launch, the onboarding wizard will guide you through setup (language, mode, hotkey, persona).

---

## How it works

1. **Hold** the hotkey (default: `Caps Lock` toggle or `Ctrl+Alt+Space`)
2. **Speak** — recording starts immediately
3. **Release** — audio is transcribed via Groq Whisper
4. **AI formats** the text according to your active persona
5. **Text is injected** into the active window at cursor position

Total latency: **~1–2.5 seconds** from release to insertion.

---

## Personas (AI formatting profiles)

Switch persona from the tray icon menu or Settings → General.

| Persona | What it does |
|---------|-------------|
| **General User** | Minimal cleanup — punctuation only, no rephrasing |
| **IT Specialist / Developer** | Keeps IT slang (задеплоить, запушить), writes terms in correct English (API, Git, CI/CD) |
| **Manager / Entrepreneur** | Structures tasks as bullet lists with action items and deadlines |
| **Writer / Blogger / Marketer** | Preserves author style and emotional tone |
| **Medical / Legal / Researcher** | Strictly preserves professional terms, Latin, law article numbers |
| **Support Specialist** | Clear polite formulations, structured troubleshooting steps |
| **HR / Recruiter** | Business style, corporate vocabulary |
| **Teacher / Trainer** | Pedagogical style, methodological terms |

---

## App-Awareness (auto persona switching)

YapClean detects the active application and switches persona automatically:

| App | Auto persona |
|-----|-------------|
| VS Code, Cursor, PyCharm | IT Specialist / Developer |
| PowerShell, Terminal | IT Specialist / Developer |
| Slack, Telegram, Discord | General User |
| Word, Notion | Manager / Entrepreneur |
| Chrome, Firefox | General User |

You can add custom rules in **Settings → App Rules**.

---

## Translation mode

Enable **"Translate to keyboard layout"** in Settings to get automatic translation:

- Russian keyboard layout active → text stays in Russian
- English keyboard layout active → text is first formatted by persona, then translated to English

Example: say *"нам нужно задеплоить проект"* with EN layout active →  
`We need to deploy the project.`

---

## Hotkey modes

| Mode | Behavior |
|------|----------|
| **Hold-to-talk** | Hold hotkey to record, release to process |
| **Toggle** | First press starts recording, second press stops |

Caps Lock is always toggle mode.

---

## Settings

Open settings from the tray icon → **Settings**, or run:

```bash
python main.py --settings
```

### Tabs

- **General** — API keys, hotkey, language, STT/LLM provider, microphone, bypass LLM toggle
- **LLM Profiles** — edit or add custom formatting presets
- **System Prompt** — edit the global AI system prompt
- **App Rules** — bind personas to specific apps (process name → persona)

### API Keys

Keys are stored securely in the OS keychain (Windows Credential Manager), never in plain text files.

Supported providers:
- **STT:** Groq Whisper (default, free), Deepgram Nova-3, OpenAI Whisper, local faster-whisper
- **LLM:** Groq Llama (default, free), OpenAI GPT-4o-mini, Ollama (local)

---

## Quick config via script

Instead of the UI, you can configure everything by editing `setup_keys.py`:

```python
GROQ_API_KEY    = "gsk_..."   # Required — https://console.groq.com
DEEPGRAM_KEY    = ""          # Optional
OPENAI_KEY      = ""          # Optional

STT_PROVIDER    = "groq"      # groq | deepgram | openai | local
LLM_PROVIDER    = "groq"      # groq | openai | ollama
ACTIVE_PERSONA  = "General User"
HOTKEY          = "caps lock"
DICTATION_LANG  = "Russian"
```

Then run: `python setup_keys.py`

---

## Notion integration (optional)

Send voice notes to a Notion database automatically.

1. Enable **Notion Integration** in Settings
2. Add your Notion API key and Database ID
3. Set a trigger word (e.g. `заметка`)
4. Say the trigger word at the start or end of your dictation

The note is automatically categorized by topic and tags via AI.

---

## Troubleshooting

**Text not inserting?**  
Make sure the target window is focused before speaking. Some apps (games, admin windows) block simulated keyboard input.

**Wrong language output?**  
Check that `translate_to_layout` is set correctly in Settings. If you want Russian output, make sure the Russian keyboard layout is active when you press the hotkey.

**"прод" transcribed as "прот"?**  
This is a Whisper limitation. Use IT Specialist persona — it passes a vocabulary hint to the STT model to improve recognition of Russian IT slang.

**App-Awareness not switching?**  
The persona is resolved at the moment you press the hotkey. Make sure the target app window is focused (not the terminal running YapClean).

**Onboarding keeps appearing?**  
Run `python setup_keys.py` — it sets `onboarding_complete: true` automatically.

---

## Running tests

```bash
python -m pytest tests/
```

104 property-based tests covering audio pipeline, LLM middleware, clipboard injection, provider fallback chain, and Notion trigger logic.

---

## Build (Windows)

```bash
python build_windows.py
```

Output: `dist/YapClean/YapClean.exe`

To create an installer (requires [NSIS](https://nsis.sourceforge.io/)):
```bash
makensis installer.nsi
```

---

## Requirements

- Windows 10/11 (macOS and Linux support in progress)
- Python 3.10+
- Free [Groq API key](https://console.groq.com) for STT + LLM

---

## Support

Questions? Issues? Feedback? Contact us at [founder@yapclean.tech](mailto:founder@yapclean.tech) or open an issue on GitHub.

