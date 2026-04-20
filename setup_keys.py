"""
setup_keys.py — Quick setup script to configure YapClean API keys and settings.
Run: python setup_keys.py
"""
import json
import os

# ─── Paste your API keys here ─────────────────────────────────────────────────

GROQ_API_KEY    = ""   # Get at: https://console.groq.com  (free, fast)
DEEPGRAM_KEY    = ""   # Optional: https://console.deepgram.com
OPENAI_KEY      = ""   # Optional: https://platform.openai.com

# ─── Settings ─────────────────────────────────────────────────────────────────

STT_PROVIDER    = "groq"    # groq | deepgram | openai | local
LLM_PROVIDER    = "groq"    # groq | openai | ollama
ACTIVE_PERSONA  = "General User"
HOTKEY          = "ctrl+alt+space"
DICTATION_LANG  = "Russian"

# ──────────────────────────────────────────────────────────────────────────────

def main():
    # Save keys to keyring
    import keyring
    SERVICE = "YapClean"

    if GROQ_API_KEY:
        keyring.set_password(SERVICE, "api_key", GROQ_API_KEY)
        print(f"✓ Groq API key saved")
    if DEEPGRAM_KEY:
        keyring.set_password(SERVICE, "deepgram_api_key", DEEPGRAM_KEY)
        print(f"✓ Deepgram key saved")
    if OPENAI_KEY:
        keyring.set_password(SERVICE, "openai_api_key", OPENAI_KEY)
        print(f"✓ OpenAI key saved")

    # Update config.json
    app_dir = os.path.join(os.getenv("APPDATA", ""), "YapClean")
    config_path = os.path.join(app_dir, "config.json")
    os.makedirs(app_dir, exist_ok=True)

    config = {}
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

    config.update({
        "stt_provider": STT_PROVIDER,
        "llm_provider": LLM_PROVIDER,
        "active_persona": ACTIVE_PERSONA,
        "hotkey": HOTKEY,
        "dictation_language": DICTATION_LANG,
        "onboarding_complete": True,
        "bypass_llm": False,
    })

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

    print(f"✓ Config saved to: {config_path}")
    print(f"  STT: {STT_PROVIDER}, LLM: {LLM_PROVIDER}")
    print(f"  Hotkey: {HOTKEY}, Language: {DICTATION_LANG}")
    print("\nDone! Run: python main.py")

if __name__ == "__main__":
    main()
