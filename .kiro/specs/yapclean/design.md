# YapClean — Design Document

## 1. Overview

This document describes the technical architecture of YapClean — a cross-platform desktop voice input utility with AI-powered text formatting. It covers module structure, data flows, component interfaces, and platform-specific implementation decisions.

Language stack: **Python 3.11+**
UI framework: **CustomTkinter** (settings/onboarding), **pystray** (system tray)
Packaging: **PyInstaller** → platform-specific installers

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        main.py (App)                        │
│  Orchestrates lifecycle, wires components, runs event loop  │
└──────┬──────────┬──────────┬──────────┬────────────────────┘
       │          │          │          │
  HotkeyListener  TrayApp  Pipeline  ConfigManager
       │                     │
  pynput global          ┌───┴────────────────────┐
  hotkey (cross-         │  core/pipeline.py       │
  platform)              │  STT → LLM → Inject     │
                         └───┬────────┬────────────┘
                             │        │
                      STTProvider  LLMProvider
                      (Adapter)    (Adapter)
                             │        │
                    ┌────────┘        └────────┐
               Groq/Deepgram/            Groq/OpenAI/
               OpenAI/Local              Ollama/Cloud
```

### Core Data Flow

```
Hotkey Press
    │
    ▼
AudioManager.start_recording()
    │
Hotkey Release
    │
    ▼
AudioManager.stop_recording() → audio.wav (temp)
    │
    ▼
AppAwarenessManager.get_active_process() → process_name
PersonaRouter.resolve(process_name) → persona
    │
    ▼
STTProvider.transcribe(audio.wav, language, prompt_hint) → raw_text
    │
    ▼
[bypass=False?]
    │  YES
    ▼
LLMProvider.refine(raw_text, persona) → refined_text
RefusalDetector.check(refined_text) → raw_text (fallback if refusal)
    │
    ▼
ClipboardInjector.inject(refined_text)
    │
    ▼
[Notion trigger?] → NotionIntegration.send(text)
    │
    ▼
temp file deleted (finally)
```

---

## 3. Module Structure

```
yapclean/
├── main.py                        # App entry point, lifecycle
├── core/
│   ├── pipeline.py                # Main processing orchestrator
│   ├── audio_manager.py           # Mic recording, device selection
│   ├── hotkey_listener.py         # Cross-platform hotkey (pynput)
│   ├── clipboard_injector.py      # Text injection + Smart Undo
│   └── app_awareness.py           # Active window process detection
├── providers/
│   ├── base.py                    # Abstract STTProvider, LLMProvider
│   ├── registry.py                # Provider factory & fallback chain
│   ├── stt/
│   │   ├── groq_stt.py
│   │   ├── deepgram_stt.py
│   │   ├── openai_stt.py
│   │   └── local_whisper.py       # faster-whisper
│   └── llm/
│       ├── groq_llm.py
│       ├── openai_llm.py
│       ├── ollama_llm.py
│       └── cloud_llm.py           # YapClean Pro backend
├── personas/
│   ├── prompts.py                 # Built-in persona definitions
│   ├── router.py                  # App-Awareness → Persona resolver
│   └── refusal_detector.py        # LLM refusal/hallucination guard
├── storage/
│   ├── keyring_manager.py         # Secure key storage (OS keychain)
│   └── config_manager.py          # Non-sensitive settings (JSON)
├── i18n/
│   ├── translator.py              # i18n engine
│   └── locales/
│       ├── en.json
│       └── ru.json
├── ui/
│   ├── tray_app.py                # System tray (pystray)
│   ├── settings_ui.py             # Settings window (CustomTkinter)
│   └── onboarding.py              # First-run wizard
├── integrations/
│   └── notion.py
└── platform/
    ├── autostart.py               # OS-specific autostart
    └── notifications.py           # OS-specific system notifications
```

---

## 4. Component Design

### 4.1 providers/base.py — Abstract Interfaces

```python
from abc import ABC, abstractmethod

class STTProvider(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str, language: str, prompt_hint: str = "") -> str:
        """Returns raw transcript string. Raises ProviderError on failure."""

class LLMProvider(ABC):
    @abstractmethod
    def refine(self, text: str, persona: str, system_prompt: str) -> str:
        """Returns refined text. Raises ProviderError on failure."""

class ProviderError(Exception):
    pass
```

### 4.2 providers/registry.py — Factory & Fallback Chain

```python
class ProviderRegistry:
    def get_stt_chain(self) -> list[STTProvider]:
        """Returns ordered list of STT providers for fallback."""

    def get_llm_provider(self) -> LLMProvider:
        """Returns active LLM provider."""

    def transcribe_with_fallback(self, audio_path, language, prompt_hint) -> str:
        """Tries each STT provider in chain, raises if all fail."""
```

Fallback order (configurable by user):
1. Primary provider (user-selected)
2. Secondary provider (user-selected or auto)
3. Local Whisper (always available as last resort if installed)

### 4.3 core/pipeline.py — Processing Orchestrator

```python
class Pipeline:
    def __init__(self, registry, injector, app_awareness, persona_router,
                 refusal_detector, notion, config):
        ...

    def process(self, audio_path: str) -> None:
        """Full pipeline: STT → LLM → Inject → Notion (optional)"""
        process_name = self.app_awareness.get_active_process()
        persona = self.persona_router.resolve(process_name)
        language = self.config.get("dictation_language", "en")
        prompt_hint = self.config.get("stt_prompt_hint", "")

        raw_text = self.registry.transcribe_with_fallback(audio_path, language, prompt_hint)
        if not raw_text.strip():
            return

        if self.config.get("bypass_llm", False):
            final_text = raw_text
        else:
            system_prompt = self.persona_router.get_system_prompt(persona)
            refined = self.registry.get_llm_provider().refine(raw_text, persona, system_prompt)
            final_text = self.refusal_detector.check(refined, fallback=raw_text)

        self.injector.inject(final_text)

        if self.notion.should_trigger(raw_text):
            threading.Thread(target=self.notion.send, args=(final_text,), daemon=True).start()
```

### 4.4 personas/refusal_detector.py — LLM Guard

```python
REFUSAL_PATTERNS = [
    r"^i'?m sorry",
    r"^as an ai",
    r"^i cannot",
    r"^извините,?\s*я не",
    r"^как языковая модель",
    r"^here is your",
    r"^вот ваш текст",
    r"^sure[,!]",
]

class RefusalDetector:
    def check(self, llm_output: str, fallback: str) -> str:
        """Returns fallback (raw transcript) if LLM output matches refusal patterns."""
        text = llm_output.strip().lower()
        for pattern in REFUSAL_PATTERNS:
            if re.match(pattern, text, re.IGNORECASE):
                logger.warning(f"[RefusalDetector] LLM refusal detected, using raw transcript")
                return fallback
        return llm_output
```

### 4.5 core/app_awareness.py — Active Window Detection

```python
class AppAwarenessManager:
    def get_active_process(self) -> str:
        """Returns process name of foreground window. Platform-specific."""
        # Windows: ctypes GetForegroundWindow + GetWindowThreadProcessId + psutil
        # macOS:   NSWorkspace.sharedWorkspace().frontmostApplication.localizedName
        # Linux:   subprocess xdotool getactivewindow getwindowpid + psutil
        ...
```

**Privacy guarantee:** Only the process name (e.g. `Code.exe`) is read. No window title, no content, no screenshots.

### 4.6 personas/router.py — Persona Resolver

```python
DEFAULT_APP_BINDINGS = {
    "code": "IT Specialist / Developer",
    "cursor": "IT Specialist / Developer",
    "idea64": "IT Specialist / Developer",
    "pycharm": "IT Specialist / Developer",
    "slack": "General User",
    "telegram": "General User",
    "discord": "General User",
    "winword": "Manager / Entrepreneur",
    "notion": "Manager / Entrepreneur",
    "chrome": "General User",
    "firefox": "General User",
}

class PersonaRouter:
    def resolve(self, process_name: str) -> str:
        """Returns persona name. Falls back to user default if no binding found."""
        key = process_name.lower().replace(".exe", "")
        bindings = self.config.get("app_bindings", DEFAULT_APP_BINDINGS)
        return bindings.get(key, self.config.get("active_persona", "General User"))
```

### 4.7 core/clipboard_injector.py — Text Injection + Smart Undo

```python
class ClipboardInjector:
    def inject(self, text: str) -> None:
        if not text:
            return
        old_clipboard = pyperclip.paste()
        try:
            pyperclip.copy(text)
            time.sleep(0.05)
            keyboard.send("ctrl+v")   # Ctrl+V pastes as single undo-able action
            time.sleep(0.15)
            # Smart Undo: Ctrl+V in most apps registers as one undo step.
            # User can press Ctrl+Z once to remove the entire inserted block.
            # No additional implementation needed — this is native OS behavior.
        except Exception as e:
            logger.error(f"[Injector] {e}")
        finally:
            pyperclip.copy(old_clipboard)
```

**Smart Undo note:** Ctrl+V in virtually all text editors (VS Code, Word, Notepad, browsers) registers as a single undo action. One Ctrl+Z removes the entire pasted block. No custom undo stack needed.

### 4.8 core/audio_manager.py — Recording + Silence Detection

```python
class AudioManager:
    MIN_DURATION_SEC = 0.2      # FR-1.5: lowered from 0.5
    SILENCE_RMS_THRESHOLD = 0.001

    def stop_recording(self) -> str | None:
        audio = np.concatenate(self.audio_data)
        duration = len(audio) / SAMPLE_RATE
        rms = np.sqrt(np.mean(np.square(audio)))

        # FR-1.5: BOTH conditions must be true to discard
        if duration < self.MIN_DURATION_SEC and rms < self.SILENCE_RMS_THRESHOLD:
            return None

        # Save to temp WAV and return path
        ...
```

### 4.9 storage/keyring_manager.py — Secure Key Storage

```python
import keyring

SERVICE_NAME = "YapClean"

class KeyringManager:
    def save(self, key_name: str, value: str) -> None:
        keyring.set_password(SERVICE_NAME, key_name, value)

    def get(self, key_name: str) -> str | None:
        return keyring.get_password(SERVICE_NAME, key_name)

    def delete(self, key_name: str) -> None:
        try:
            keyring.delete_password(SERVICE_NAME, key_name)
        except keyring.errors.PasswordDeleteError:
            pass
```

Backed by:
- **Windows:** Windows Credential Manager (DPAPI-encrypted)
- **macOS:** Keychain
- **Linux:** SecretService (GNOME Keyring / KWallet)

Keys stored: `groq_api_key`, `deepgram_api_key`, `openai_api_key`, `yapclean_pro_token`

### 4.10 storage/config_manager.py — Non-Sensitive Settings

Config stored at:
- Windows: `%APPDATA%\YapClean\config.json`
- macOS: `~/Library/Application Support/YapClean/config.json`
- Linux: `~/.config/YapClean/config.json`

```json
{
  "hotkey": "ctrl+alt+space",
  "hotkey_mode": "hold",
  "dictation_language": "ru",
  "active_persona": "General User",
  "bypass_llm": false,
  "stt_provider": "groq",
  "llm_provider": "groq",
  "app_bindings": {},
  "ui_language": "en",
  "autostart": false,
  "enable_notion": false,
  "notion_trigger_word": "note",
  "notion_database_id": "",
  "custom_personas": {},
  "custom_system_prompt": "",
  "onboarding_complete": false,
  "app_mode": "byok"
}
```

**No secrets in this file.** All API keys go to keyring.

### 4.11 core/hotkey_listener.py — Cross-Platform Hotkey

Replaces `keyboard` lib with `pynput` — works on all platforms without admin rights.

```python
from pynput import keyboard as pynput_kb

class HotkeyListener:
    def __init__(self, on_press_cb, on_release_cb):
        self.hotkey_combo = self._parse(config.get("hotkey"))
        self.mode = config.get("hotkey_mode", "hold")  # "hold" or "toggle"
        self._pressed_keys = set()
        self._recording = False

    def start(self):
        with pynput_kb.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        ) as listener:
            listener.join()
```

Hold-to-talk: fires `on_press` when combo held, `on_release` when released.
Toggle: fires `on_press` on first combo, `on_release` on second combo.

### 4.12 i18n/translator.py — Localization Engine

```python
class Translator:
    def __init__(self, locale: str = "en"):
        self._strings = self._load(locale)

    def t(self, key: str, **kwargs) -> str:
        """Returns translated string. Falls back to English if key missing."""
        template = self._strings.get(key, self._fallback.get(key, key))
        return template.format(**kwargs) if kwargs else template

# Global singleton
_translator = Translator()
def t(key, **kwargs): return _translator.t(key, **kwargs)
```

Usage in UI:
```python
from i18n.translator import t
ctk.CTkLabel(text=t("settings.title"))
```

Locale files (`locales/en.json`):
```json
{
  "settings.title": "YapClean Settings",
  "settings.hotkey": "Hotkey",
  "settings.language": "Dictation Language",
  "onboarding.step1.title": "Choose your mode",
  "tray.recording": "Recording...",
  "tray.processing": "Processing...",
  "tray.settings": "Settings",
  "tray.exit": "Exit"
}
```

---

## 5. STT Providers — Implementation Details

### 5.1 Groq Whisper (groq_stt.py)

```python
class GroqSTT(STTProvider):
    def transcribe(self, audio_path, language, prompt_hint="") -> str:
        with open(audio_path, "rb") as f:
            result = self.client.audio.transcriptions.create(
                file=(os.path.basename(audio_path), f.read()),
                model="whisper-large-v3",
                language=language,
                prompt=prompt_hint,   # FR-2.5: code-switching hint
                response_format="text"
            )
        return str(result)
```

### 5.2 Code-Switching Prompt Hint (FR-2.5)

Default `stt_prompt_hint` per persona:

| Persona | Prompt hint |
|---------|-------------|
| IT Specialist | `"commit, push, merge, branch, deploy, API, backend, frontend, PR, staging, Docker, CI/CD"` |
| Manager | `"KPI, deadline, action items, stakeholder, roadmap"` |
| Medical | `"diagnosis, anamnesis, ICD-10, mg, ml, contraindication"` |
| General | `""` (empty) |

### 5.3 Local Whisper (local_whisper.py)

Uses `faster-whisper` for CPU/GPU inference:

```python
from faster_whisper import WhisperModel

class LocalWhisperSTT(STTProvider):
    def __init__(self, model_size="base", device="cpu"):
        self.model = WhisperModel(model_size, device=device, compute_type="int8")

    def transcribe(self, audio_path, language, prompt_hint="") -> str:
        segments, _ = self.model.transcribe(audio_path, language=language,
                                             initial_prompt=prompt_hint)
        return " ".join(s.text for s in segments).strip()
```

---

## 6. LLM Providers — Implementation Details

### 6.1 Groq LLM (groq_llm.py)

```python
class GroqLLM(LLMProvider):
    MODEL = "llama-3.1-8b-instant"

    def refine(self, text, persona, system_prompt) -> str:
        response = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": f"{system_prompt}\n\nActive Persona: {persona}"},
                {"role": "user", "content": f"<transcription>\n{text}\n</transcription>"}
            ],
            model=self.MODEL,
            max_tokens=2048,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
```

### 6.2 Persona System Prompt Construction

```python
# personas/prompts.py

UNIVERSAL_SYSTEM_PROMPT = """
You are a universal smart text editor. Process the raw transcribed text based on the selected Persona.
Output ONLY the formatted text. No preambles, no explanations.

Universal rules:
1. Fix grammar, syntax, punctuation.
2. Remove filler words (uhm, like, you know, ну, типа, короче).
3. Split into paragraphs if topic changes or text is long.
4. Output ONLY the result.
"""

PERSONA_INSTRUCTIONS = {
    "IT Specialist / Developer": "Keep IT slang naturally (deploy, push, merge, bug). Write technical terms in correct English (API, IDE, Mac, framework).",
    "Manager / Entrepreneur": "Focus on conciseness and structure. Use bullet lists for tasks. Business style (action items, deadlines).",
    "Writer / Blogger / Marketer": "Preserve author's style, emotional tone, speech rhythm. Improve readability without making it dry.",
    "Medical / Legal / Researcher": "Strictly preserve professional terms, Latin, abbreviations, law article numbers. Accuracy over style.",
    "General User": "Natural everyday style. Clean correct text without changing meaning or vocabulary.",
    "Support Specialist": "Clear polite formulations. Structure troubleshooting steps. Professional tone.",
    "HR / Recruiter": "Business style. Clarity in requirements and conditions. Corporate vocabulary.",
    "Teacher / Trainer": "Pedagogical style. Structure. Clarity of explanations. Methodological terms.",
}

def build_system_prompt(persona: str, custom_prompt: str = "") -> str:
    base = custom_prompt or UNIVERSAL_SYSTEM_PROMPT
    instruction = PERSONA_INSTRUCTIONS.get(persona, "")
    return f"{base}\n\nPersona-specific rules:\n{instruction}"
```

---

## 7. UI Design

### 7.1 System Tray Menu

```
YapClean ●  (icon: black=idle, red=recording, yellow=processing)
├── Active Persona: [General User ▾]
│   ├── IT Specialist / Developer
│   ├── Manager / Entrepreneur
│   ├── Writer / Blogger / Marketer
│   ├── Medical / Legal / Researcher
│   ├── General User ✓
│   ├── Support Specialist
│   ├── HR / Recruiter
│   ├── Teacher / Trainer
│   └── [Custom personas...]
├── ─────────────────
├── Settings...
├── About YapClean
└── Exit
```

### 7.2 Settings Window — Tab Structure

```
┌─────────────────────────────────────────────┐
│  YapClean Settings                    [×]   │
├─────────────────────────────────────────────┤
│  [General] [Personas] [App Rules] [Advanced]│
├─────────────────────────────────────────────┤
│                                             │
│  General Tab:                               │
│  ┌─ Mode ──────────────────────────────┐   │
│  │  ○ Local (faster-whisper)           │   │
│  │  ● BYOK (your API keys)             │   │
│  │  ○ Pro (yapclean.tech)              │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  STT Provider:  [Groq Whisper      ▾]      │
│  LLM Provider:  [Groq Llama        ▾]      │
│  Groq API Key:  [••••••••••••]  [Show]     │
│                                             │
│  Hotkey:        [Ctrl+Alt+Space    ▾]      │
│  Mode:          ○ Hold-to-talk  ● Toggle   │
│  Language:      [Russian               ▾]  │
│  Microphone:    [Default Mic           ▾]  │
│                                             │
│  ☑ Bypass LLM (insert raw transcript)      │
│  ☑ Autostart with system                   │
│  Interface language: [English          ▾]  │
│                                             │
└─────────────────────────────────────────────┘
```

```
App Rules Tab (App-Awareness):
┌─────────────────────────────────────────────┐
│  Auto-switch persona by active app          │
│                                             │
│  Process Name      →  Persona              │
│  ─────────────────────────────────────────  │
│  code              →  IT Specialist    [✕] │
│  cursor            →  IT Specialist    [✕] │
│  slack             →  General User     [✕] │
│  winword           →  Manager          [✕] │
│                                             │
│  [+ Add Rule]                               │
└─────────────────────────────────────────────┘
```

### 7.3 Onboarding Wizard (3 steps)

```
Step 1: Welcome + Language
┌─────────────────────────────────────────────┐
│  🎙 Welcome to YapClean                     │
│  Voice input, cleaned by AI                 │
│                                             │
│  Interface language:                        │
│  [English ▾]  [Русский]  [Українська]      │
│                                             │
│  Choose your mode:                          │
│  ┌──────────────────────────────────────┐  │
│  │ 🔒 Local    — 100% private, offline  │  │
│  │ 🔑 BYOK     — your API keys          │  │
│  │ ☁️  Pro      — yapclean.tech          │  │
│  └──────────────────────────────────────┘  │
│                              [Next →]       │
└─────────────────────────────────────────────┘

Step 2: API Key (if BYOK) / Login (if Pro) / Model select (if Local)

Step 3: Hotkey + Persona
┌─────────────────────────────────────────────┐
│  Almost done!                               │
│                                             │
│  Your hotkey:  [Ctrl+Alt+Space ▾]          │
│  Your persona: [General User   ▾]          │
│                                             │
│  [← Back]                    [Finish ✓]    │
└─────────────────────────────────────────────┘
```

---

## 8. Platform-Specific Implementation

### 8.1 Autostart (platform/autostart.py)

```python
import sys, platform

def enable_autostart(app_name: str, exe_path: str):
    os_name = platform.system()
    if os_name == "Windows":
        _windows_autostart(app_name, exe_path)
    elif os_name == "Darwin":
        _macos_launchagent(app_name, exe_path)
    elif os_name == "Linux":
        _linux_systemd(app_name, exe_path)
```

- **Windows:** `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`
- **macOS:** `~/Library/LaunchAgents/tech.yapclean.plist`
- **Linux:** `~/.config/systemd/user/yapclean.service`

### 8.2 System Notifications (platform/notifications.py)

```python
def notify(title: str, message: str, level: str = "info"):
    os_name = platform.system()
    if os_name == "Windows":
        # winotify or plyer
    elif os_name == "Darwin":
        # osascript display notification
    elif os_name == "Linux":
        # notify-send
```

### 8.3 macOS Permissions (Info.plist)

Required keys for PyInstaller `.app` bundle:
```xml
<key>NSMicrophoneUsageDescription</key>
<string>YapClean needs microphone access to record your voice for transcription.</string>
<key>NSAccessibilityUsageDescription</key>
<string>YapClean needs accessibility access to detect the active application for auto persona switching.</string>
```

First-run permission request flow:
1. App launches → checks `AVCaptureDevice.authorizationStatus` for microphone
2. If not granted → shows native macOS permission dialog
3. If denied → shows in-app guidance to System Preferences

---

## 9. Build & Packaging

### 9.1 PyInstaller Config (yapclean.spec)

```python
# Key hidden imports needed
hiddenimports=[
    "customtkinter", "pystray", "PIL",
    "pynput", "sounddevice", "soundfile",
    "keyring", "keyring.backends.Windows",
    "keyring.backends.macOS", "keyring.backends.SecretService",
    "faster_whisper",
]
```

### 9.2 GitHub Actions CI/CD

```yaml
# .github/workflows/build.yml
on:
  push:
    tags: ["v*"]

jobs:
  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements.txt
      - run: python build.py
      - uses: actions/upload-artifact@v4
        with: { name: YapClean-Windows, path: dist/YapClean-Setup.exe }

  build-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements.txt
      - run: python build.py
      # Sign + notarize with Apple credentials from secrets

  build-linux:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements.txt
      - run: python build.py
      # Package as AppImage
```

---

## 10. Dependencies (updated requirements.txt)

```
# Core
pynput>=1.7.6          # Cross-platform hotkey (replaces keyboard)
sounddevice>=0.4.6
soundfile>=0.12.1
numpy>=1.26.4
pyperclip>=1.8.2

# UI
customtkinter>=5.2.2
pystray>=0.19.5
Pillow>=10.2.0

# API Clients
groq>=1.1.2
openai>=1.30.0
requests>=2.31.0

# Secure Storage
keyring>=24.0.0

# Local STT (optional, installed on demand)
faster-whisper>=1.0.0

# Integrations
# notion-client>=2.2.1  (optional)

# Build
pyinstaller>=6.10.0

# Dev / Testing
hypothesis>=6.100.0    # Property-based testing
pytest>=8.0.0
```

---

## 11. Security Architecture Summary

| Data type | Storage | Leaves device? |
|-----------|---------|----------------|
| API keys | OS Keychain (keyring) | Never |
| App settings | config.json (plain) | Never |
| Audio recording | Temp file (deleted after use) | Only if cloud STT selected |
| Transcript text | Memory only | Only if cloud LLM selected |
| Active window name | Memory only | Never |
| Screen content | Never captured | Never |

**No-Spy Policy (NFR-3.5):** Zero screen capture libraries in dependencies. Verifiable by `pip show mss` / `pip show pyautogui` — neither will be installed.
