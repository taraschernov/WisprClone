# Project Structure

## Root-Level Entry Points
- `main.py` — app entry point; instantiates `App`, starts hotkey listener, tray, config watcher
- `config.py` — thin convenience wrappers over `ConfigManager` and `KeyringManager`
- `settings_ui.py` — standalone settings window (also launched via `--settings` flag)
- `tray_app.py` — system tray icon and menu
- `hotkey_listener.py` — global hotkey capture via `pynput`
- `audio_manager.py` — microphone recording, WAV file output
- `clipboard_injector.py` — text injection into active window via clipboard

## Module Directories

```
core/
  pipeline.py         # Orchestrates full STT → LLM → inject flow
  app_awareness.py    # Detects active process name via psutil

providers/
  base.py             # Abstract base classes: STTProvider, LLMProvider, ProviderError
  registry.py         # ProviderRegistry — builds provider chains, handles STT fallback
  stt/                # STT implementations: groq_stt, deepgram_stt, openai_stt, local_whisper
  llm/                # LLM implementations: groq_llm, openai_llm, ollama_llm

personas/
  prompts.py          # build_system_prompt(persona, custom_prompt) → str
  router.py           # PersonaRouter — maps process name → persona
  refusal_detector.py # Detects LLM refusals, falls back to raw transcript
  stt_hints.py        # Per-persona vocabulary hints passed to STT

storage/
  config_manager.py   # ConfigManager — reads/writes %APPDATA%\YapClean\config.json
  keyring_manager.py  # KeyringManager — OS keychain access (never write secrets to disk)

app_platform/
  autostart.py        # Windows autostart registry entry
  notifications.py    # Desktop notifications via plyer

utils/
  logger.py           # Rotating file + console logger; sanitizes API keys from logs
  single_instance.py  # Mutex-based single-instance guard

i18n/
  translator.py       # Translator singleton; t(key) for all user-facing strings
  locales/            # en.json, ru.json

integrations/
  notion.py           # Notion API: categorize and send voice notes

ui/
  onboarding.py       # First-launch wizard

tests/                # pytest + hypothesis test suite (mirrors module structure)
```

## Key Architectural Patterns

- **Provider pattern** — all STT and LLM backends implement abstract base classes in `providers/base.py`. Add new providers by subclassing `STTProvider` or `LLMProvider` and registering in `ProviderRegistry`.
- **Singleton instances** — `config_manager` and `keyring_manager` are module-level singletons imported directly: `from storage.config_manager import config_manager`.
- **Secrets separation** — `ConfigManager` actively refuses to write known secret keys to disk. Always use `keyring_manager` for API keys.
- **Logger naming** — use hierarchical names under `"yapclean.*"` (e.g. `get_logger("yapclean.pipeline")`). The root `"yapclean"` logger is configured once in `setup_logger()`.
- **i18n** — all user-facing strings go through `t(key)` from `i18n.translator`. Add keys to both `en.json` and `ru.json`.
- **Non-blocking pipeline** — audio processing runs in a daemon thread (`threading.Thread(daemon=True)`) to keep the UI responsive.
- **Config hot-reload** — `watchdog` monitors `config.json`; runtime-safe keys are reloaded without restart. Hotkey changes trigger a listener restart.

## Build Artifacts (gitignored)
- `dist/` — PyInstaller output
- `build/` — PyInstaller intermediate files
- `__pycache__/` — bytecode cache
