# Tech Stack & Build System

## Language & Runtime
- Python 3.10+
- Windows 10/11 primary target

## Key Libraries
| Purpose | Library |
|---|---|
| Audio capture | `sounddevice`, `soundfile`, `numpy` |
| Hotkey listening | `pynput` |
| System tray | `pystray`, `Pillow` |
| Settings UI | `customtkinter` |
| Clipboard injection | `pyperclip` |
| STT — Groq Whisper | `groq` |
| STT — OpenAI Whisper | `openai` |
| STT — local | `faster-whisper` (optional) |
| LLM — Groq | `groq` |
| LLM — OpenAI | `openai` |
| LLM — Ollama | `requests` |
| Secret storage | `keyring` |
| Config file watching | `watchdog` |
| Notifications | `plyer` |
| Process detection | `psutil` |
| Packaging | `pyinstaller` |
| Testing | `pytest`, `hypothesis` |

## Common Commands

### Run the app
```bash
python main.py
```

### Open settings directly
```bash
python main.py --settings
```

### Run tests
```bash
python -m pytest tests/
```

### Run a single test file
```bash
python -m pytest tests/test_audio.py -v
```

### Build Windows executable
```bash
python build_windows.py
# Output: dist/YapClean/YapClean.exe
```

### Create Windows installer (requires NSIS)
```bash
makensis installer.nsi
```

## Configuration Storage
- Non-sensitive settings: `%APPDATA%\YapClean\config.json`
- API keys: Windows Credential Manager via `keyring` (service name: `"YapClean"`)
- Logs: `%APPDATA%\YapClean\logs\yapclean.log` (rotating, 5MB × 3)

## Testing
- Framework: `pytest` with `hypothesis` for property-based tests
- Test directory: `tests/`
- Config: `pytest.ini` — runs with `-v --tb=short`
- 104 property-based tests covering audio pipeline, LLM middleware, clipboard injection, provider fallback, and Notion trigger logic
- Tests use mocks/stubs — no real API calls required
