# YapClean — Product Overview

YapClean is a Windows desktop voice dictation utility that transcribes speech and formats it through an AI layer before injecting the result into the active window at cursor position.

## Core Flow
1. User holds/toggles a hotkey → audio recording starts
2. Release → audio is sent to an STT provider (Groq Whisper by default)
3. Raw transcript is refined by an LLM using the active persona's system prompt
4. Optional: translate output to match the active keyboard layout language
5. Formatted text is injected into the focused window via clipboard simulation

## Key Capabilities
- **Personas** — AI formatting profiles (General User, IT Specialist, Manager, Writer, Medical, etc.)
- **App-Awareness** — auto-switches persona based on the active process (e.g., VS Code → IT Specialist)
- **Translation mode** — detects keyboard layout language and translates output accordingly
- **Notion integration** — optional: sends voice notes to a Notion database, triggered by a keyword
- **Multi-provider** — swappable STT and LLM backends (Groq, OpenAI, Deepgram, Ollama, local Whisper)
- **Onboarding wizard** — first-launch UI to configure language, hotkey, persona, and API keys

## Target Platform
Windows 10/11 (macOS and Linux support in progress). Python 3.10+.

## Secrets Policy
API keys are **never** stored in config files. They are stored exclusively in the OS keychain (Windows Credential Manager) via `KeyringManager`.
