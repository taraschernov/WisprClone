# YapClean — Implementation Tasks

## Phase 1: Security & Foundation

- [x] 1. Migrate API keys to OS keychain
  - [x] 1.1 Add `keyring>=24.0.0` to requirements.txt
  - [x] 1.2 Create `storage/keyring_manager.py` with `save()`, `get()`, `delete()` methods
  - [x] 1.3 Update `storage/config_manager.py` — remove all secret fields from config.json schema
  - [x] 1.4 Update `settings_ui.py` — on save, write keys via `KeyringManager` instead of `config_manager.set()`
  - [x] 1.5 Update `api_manager.py` — read keys from `KeyringManager` instead of `config_manager.get()`
  - [x] 1.6 Write migration helper: on first run after update, move existing plain-text keys from config.json to keyring and delete them from JSON

- [x] 2. Replace `keyboard` lib with `pynput` for cross-platform hotkey
  - [x] 2.1 Add `pynput>=1.7.6` to requirements.txt, remove `keyboard` dependency
  - [x] 2.2 Rewrite `core/hotkey_listener.py` using `pynput.keyboard.Listener`
  - [x] 2.3 Implement hold-to-talk mode (press → start, release → stop)
  - [x] 2.4 Implement toggle mode (first press → start, second press → stop)
  - [x] 2.5 Support Caps Lock as toggle hotkey via pynput Key.caps_lock
  - [x] 2.6 Remove all `ctypes.WinDLL('user32')` calls from `hotkey_listener.py`

- [x] 3. Isolate platform-specific code
  - [x] 3.1 Create `platform/autostart.py` with `enable_autostart()` and `disable_autostart()` — dispatch by `platform.system()`
  - [x] 3.2 Implement Windows autostart via `winreg` (inside `if platform.system() == "Windows"` guard)
  - [x] 3.3 Implement macOS autostart via LaunchAgent plist at `~/Library/LaunchAgents/tech.yapclean.plist`
  - [x] 3.4 Implement Linux autostart via `~/.config/systemd/user/yapclean.service`
  - [x] 3.5 Remove direct `winreg` import from `settings_ui.py`, replace with call to `platform/autostart.py`
  - [x] 3.6 Create `platform/notifications.py` with `notify(title, message, level)` — dispatch by platform
  - [x] 3.7 Implement Windows notifications via `winotify` or `plyer`
  - [x] 3.8 Implement macOS notifications via `osascript`
  - [x] 3.9 Implement Linux notifications via `notify-send`

- [x] 4. Add structured logging
  - [x] 4.1 Create `utils/logger.py` — configure `logging` module, write to `{app_dir}/logs/yapclean.log` with rotation (max 5MB, 3 backups)
  - [x] 4.2 Replace all `print()` calls across all modules with `logger.info()` / `logger.error()` / `logger.warning()`
  - [x] 4.3 Ensure API keys are never logged — add sanitizer that masks strings matching `[A-Za-z0-9_\-]{20,}`

- [x] 5. Fix single-instance mechanism
  - [x] 5.1 Windows: replace temp lock-file with named mutex via `ctypes.windll.kernel32.CreateMutexW`
  - [x] 5.2 Unix (macOS/Linux): replace temp lock-file with PID lock-file at `{tmp}/yapclean.pid` — check if PID is alive via `os.kill(pid, 0)`
  - [x] 5.3 Release lock/mutex cleanly on exit in `main.py` finally block

- [x] 6. Fix config hot-reload
  - [x] 6.1 Add `watchdog>=3.0.0` to requirements.txt
  - [x] 6.2 Replace polling loop in `main.py:check_config_reload()` with `watchdog` `FileSystemEventHandler` watching `config.json`
  - [x] 6.3 On config change event, reload only changed keys (existing logic, just triggered by watchdog instead of timer)

---

## Phase 2: Provider Architecture & LLM Middleware

- [x] 7. Implement Provider/Adapter pattern
  - [x] 7.1 Create `providers/base.py` — abstract classes `STTProvider`, `LLMProvider`, exception `ProviderError`
  - [x] 7.2 Create `providers/registry.py` — `ProviderRegistry` with `get_stt_chain()`, `get_llm_provider()`, `transcribe_with_fallback()`
  - [x] 7.3 Create `providers/stt/groq_stt.py` — migrate existing Groq Whisper logic from `api_manager.py`
  - [x] 7.4 Create `providers/stt/deepgram_stt.py` — migrate existing Deepgram logic from `api_manager.py`
  - [x] 7.5 Create `providers/stt/openai_stt.py` — implement OpenAI Whisper API transcription
  - [x] 7.6 Create `providers/stt/local_whisper.py` — implement `faster-whisper` local transcription
  - [x] 7.7 Create `providers/llm/groq_llm.py` — migrate existing Groq LLM logic from `api_manager.py`
  - [x] 7.8 Create `providers/llm/openai_llm.py` — implement OpenAI GPT-4o-mini completion
  - [x] 7.9 Create `providers/llm/ollama_llm.py` — implement Ollama local LLM via HTTP API
  - [x] 7.10 Add retry logic with exponential backoff (3 attempts) to all cloud providers
  - [x] 7.11 Delete old `api_manager.py` after all logic is migrated

- [x] 8. Implement LLM middleware — always-on Smart Formatting
  - [x] 8.1 Create `personas/prompts.py` — `UNIVERSAL_SYSTEM_PROMPT`, `PERSONA_INSTRUCTIONS` dict for all 8 personas, `build_system_prompt(persona, custom_prompt)` function
  - [x] 8.2 Create `personas/refusal_detector.py` — `RefusalDetector.check(llm_output, fallback)` with regex patterns for LLM refusals
  - [x] 8.3 Update `core/pipeline.py` — call LLM refine **always** (not only when translation is on), pass persona and system prompt
  - [x] 8.4 Wire `RefusalDetector` into pipeline after LLM call
  - [x] 8.5 Implement Bypass mode — if `config.get("bypass_llm")` is True, skip LLM and inject raw transcript directly

- [x] 9. Implement Code-Switching STT hints (FR-2.5)
  - [x] 9.1 Create `personas/stt_hints.py` — dict mapping persona name to prompt hint string
  - [x] 9.2 Pass `prompt_hint` from `PersonaRouter` to `STTProvider.transcribe()` for providers that support it (Groq, OpenAI Whisper)
  - [x] 9.3 Deepgram does not support prompt hint — skip silently

- [x] 10. Implement App-Awareness (FR-3.9)
  - [x] 10.1 Create `core/app_awareness.py` — `AppAwarenessManager.get_active_process()` returning process name string
  - [x] 10.2 Implement Windows: `ctypes GetForegroundWindow` + `GetWindowThreadProcessId` + `psutil.Process(pid).name()`
  - [x] 10.3 Implement macOS: `NSWorkspace.sharedWorkspace().frontmostApplication.processIdentifier` via `pyobjc` or `subprocess osascript`
  - [x] 10.4 Implement Linux: `subprocess xdotool getactivewindow getwindowpid` + `psutil.Process(pid).name()`
  - [x] 10.5 Create `personas/router.py` — `PersonaRouter.resolve(process_name)` with `DEFAULT_APP_BINDINGS` dict and user-defined overrides from config
  - [x] 10.6 Wire `AppAwarenessManager` and `PersonaRouter` into `core/pipeline.py` — resolve persona before STT call

- [x] 11. Update audio silence detection (FR-1.5)
  - [x] 11.1 Change `MIN_AUDIO_DURATION_SEC` from `0.5` to `0.2` in `core/audio_manager.py`
  - [x] 11.2 Update discard logic: only discard if **both** `duration < 0.2` **AND** `rms < SILENCE_THRESHOLD_RMS` are true simultaneously

---

## Phase 3: UX, Onboarding & i18n

- [x] 12. Implement i18n system (NFR-6)
  - [x] 12.1 Create `i18n/translator.py` — `Translator` class with `t(key, **kwargs)` method and fallback to English
  - [x] 12.2 Create `i18n/locales/en.json` — all UI strings in English (settings, tray, onboarding, error messages)
  - [x] 12.3 Create `i18n/locales/ru.json` — Russian translations for all keys in en.json
  - [x] 12.4 Replace all hardcoded Russian strings in `settings_ui.py` with `t("key")` calls
  - [x] 12.5 Replace all hardcoded strings in `tray_app.py` with `t("key")` calls
  - [x] 12.6 Add `ui_language` field to config.json (default: `"en"`)
  - [x] 12.7 Add language selector dropdown to Settings → General tab

- [x] 13. Implement Onboarding Wizard (FR-4.3)
  - [x] 13.1 Create `ui/onboarding.py` — 3-step CustomTkinter wizard window
  - [x] 13.2 Step 1: language selector + mode selector (Local / BYOK / Pro) with descriptions
  - [x] 13.3 Step 2 (BYOK): API key input fields for selected providers, save to keyring on Next
  - [x] 13.4 Step 2 (Local): model size selector (tiny/base/small), download progress indicator
  - [x] 13.5 Step 2 (Pro): email + password login form, authenticate against yapclean.tech backend
  - [x] 13.6 Step 3: hotkey selector + persona selector + "Finish" button
  - [x] 13.7 Set `onboarding_complete: true` in config.json after wizard completes
  - [x] 13.8 In `main.py`: if `onboarding_complete` is False, launch onboarding before tray

- [x] 14. Update Settings UI
  - [x] 14.1 Add "App Rules" tab to `settings_ui.py` — table of process→persona bindings with Add/Delete buttons
  - [x] 14.2 Add microphone device selector dropdown (list via `sounddevice.query_devices()`)
  - [x] 14.3 Add STT provider selector dropdown
  - [x] 14.4 Add LLM provider selector dropdown
  - [x] 14.5 Add "Bypass LLM" checkbox
  - [x] 14.6 Add hotkey mode selector (Hold-to-talk / Toggle)
  - [x] 14.7 Move API key fields to use `KeyringManager` (show masked value, update on save)
  - [x] 14.8 Add interface language selector (en / ru)

- [x] 15. Update System Tray
  - [x] 15.1 Add persona submenu to tray context menu — list all personas with checkmark on active one
  - [x] 15.2 Add 4th tray icon state: yellow/orange for "processing" (STT/LLM in progress)
  - [x] 15.3 On persona switch from tray, update `config_manager` and `PersonaRouter` immediately (no restart needed)
  - [x] 15.4 Replace hardcoded strings with `t()` calls

- [x] 16. System notifications for errors
  - [x] 16.1 Call `platform/notifications.notify()` on STT provider failure (all fallbacks exhausted)
  - [x] 16.2 Call `platform/notifications.notify()` on LLM provider failure
  - [x] 16.3 Call `platform/notifications.notify()` on microphone access denied
  - [x] 16.4 Call `platform/notifications.notify()` on Notion sync failure (non-blocking, warning level)

---

## Phase 4: Packaging & Distribution

- [-] 17. Windows build
  - [x] 17.1 Update `build.py` — add all new hidden imports (`pynput`, `keyring`, `keyring.backends.Windows`, `faster_whisper`, `watchdog`)
  - [ ] 17.2 Test PyInstaller `--onedir` build on Windows 10 and Windows 11
  - [x] 17.3 Create NSIS installer script (`installer.nsi`) — install to `%PROGRAMFILES%\YapClean`, create Start Menu shortcut, uninstaller
  - [ ] 17.4 Test installer: install, run, uninstall cycle

- [-] 18. macOS build
  - [x] 18.1 Create `build_macos.py` — PyInstaller with `--windowed`, generate `.app` bundle
  - [x] 18.2 Add `Info.plist` with `NSMicrophoneUsageDescription` and `NSAccessibilityUsageDescription`
  - [x] 18.3 Create `create_dmg.sh` — package `.app` into signed `.dmg` using `create-dmg` tool
  - [x] 18.4 Configure code signing with Apple Developer certificate (via `codesign`)
  - [x] 18.5 Configure notarization via `xcrun notarytool` with App Store Connect API key
  - [ ] 18.6 Test on macOS 12 (Monterey) and macOS 14 (Sonoma): permissions dialog, hotkey, injection

- [-] 19. Linux build
  - [x] 19.1 Create `build_linux.py` — PyInstaller `--onedir` build
  - [x] 19.2 Create `package_appimage.sh` — wrap dist folder into `.AppImage` using `appimagetool`
  - [x] 19.3 Create `package_deb.sh` — create `.deb` package with proper `control` file and desktop entry
  - [ ] 19.4 Test on Ubuntu 22.04 and Ubuntu 24.04: hotkey (X11 and Wayland), injection, tray icon

- [x] 20. CI/CD pipeline
  - [x] 20.1 Create `.github/workflows/build.yml` — matrix build triggered on `v*` tags
  - [x] 20.2 Windows job: build + NSIS installer → upload artifact `YapClean-Setup-{version}.exe`
  - [x] 20.3 macOS job: build + DMG + notarize → upload artifact `YapClean-{version}.dmg`
  - [x] 20.4 Linux job: build + AppImage → upload artifact `YapClean-{version}.AppImage`
  - [x] 20.5 Create GitHub Release automatically with all 3 artifacts on tag push

---

## Phase 5: Testing

- [x] 21. Property-based tests (hypothesis)
  - [x] 21.1 `tests/test_audio.py` — CP-1.1: `stop_recording()` returns None when duration < 0.2s AND rms < threshold
  - [x] 21.2 `tests/test_audio.py` — CP-1.2: short but loud audio (single word) is NOT discarded
  - [x] 21.3 `tests/test_llm.py` — CP-2.1: `refine_text()` output never starts with refusal phrases
  - [x] 21.4 `tests/test_llm.py` — CP-2.1a: `RefusalDetector.check()` returns fallback for all known refusal patterns
  - [x] 21.5 `tests/test_llm.py` — CP-2.3: empty input returns empty string without API call
  - [x] 21.6 `tests/test_storage.py` — CP-3.1: save→get roundtrip returns same value
  - [x] 21.7 `tests/test_storage.py` — CP-3.2: config.json after save contains no strings matching API key pattern
  - [x] 21.8 `tests/test_storage.py` — CP-3.3: delete→get returns None
  - [x] 21.9 `tests/test_providers.py` — CP-4.3: fallback chain tries next provider on ProviderError
  - [x] 21.10 `tests/test_injection.py` — CP-5.1: clipboard restored to original value after inject (even on exception)
  - [x] 21.11 `tests/test_injection.py` — CP-5.2: empty text does not trigger paste
  - [x] 21.12 `tests/test_notion.py` — CP-6.1: trigger word detected only at start or end of transcript
  - [x] 21.13 `tests/test_notion.py` — CP-6.3: `enable_notion=False` makes no HTTP requests
  - [x] 21.14 `tests/test_personas.py` — CP-4.1: all STT providers implement `transcribe(audio_path, language, prompt_hint)` interface
  - [x] 21.15 `tests/test_personas.py` — CP-4.2: all LLM providers implement `refine(text, persona, system_prompt)` interface
