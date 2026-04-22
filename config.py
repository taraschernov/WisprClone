from storage.config_manager import config_manager
from storage.keyring_manager import keyring_manager
import os

def get_api_key():
    """Get API key from secure keyring. Fails fast if not configured."""
    api_key = keyring_manager.get("api_key")
    if not api_key:
        raise ValueError(
            "API key not found in keyring. Run: python setup_keys.py"
        )
    if not api_key.startswith("gsk_") or len(api_key) < 30:
        raise ValueError("Invalid Groq API key format")
    return api_key

def get_hotkey():
    return config_manager.get("hotkey") or "ctrl+shift"

def get_notion_api_key():
    return keyring_manager.get("notion_api_key") or os.getenv("NOTION_API_KEY", "")

def get_notion_database_id():
    return config_manager.get("notion_database_id") or os.getenv("NOTION_DATABASE_ID", "")

def get_enable_notion():
    return config_manager.get("enable_notion")

def get_notion_trigger_word():
    return config_manager.get("notion_trigger_word", "")

# STT Config
WHISPER_MODEL = "whisper-large-v3"

# LLM Config
LLM_MODEL = "llama-3.3-70b-versatile"

DEFAULT_SYSTEM_PROMPT = """### Role
You are an expert Linguistic Processor specializing in transforming raw speech-to-text (STT) transcripts into polished, professional, and highly readable content.

### Objective
Your goal is to process the provided transcript according to the selected mode. Eliminate verbal clutter (filler words like "uhm", "basically", "типа", "ну") without stripping the text of its technical accuracy or original intent.

### Universal Rules (CRITICAL):
- **No Meta-Talk:** Output ONLY the processed text. No "Here is your text" or "Sure!".
- **Preserve Jargon:** Do not translate or modify industry-specific terms (e.g., "stack", "PR", "инстанс").
- **Preserve Formatting:** If the input implies a list, use Markdown bullet points.
- **Unclear Words:** If a word is nonsensical, leave it as is. Do not guess if it changes the meaning."""

DEFAULT_PRESETS = {
    "Strict Cleanup": "Minimal intervention. Fix only obvious grammar/punctuation errors and remove verbal debris. Keep the original structure exactly as is.",
    "Professional Polish": "Transform the text into a structured, professional format suitable for business correspondence or documentation. Improve flow and clarity while maintaining all key facts.",
    "Creative/Casual": "Maintain a natural conversational style, emotions, and unique author's vocabulary. Remove stutters and filler words but keep the vibe alive.",
    "Developer Mode": "Focus on technical accuracy. Keep all technical terms, code snippets, and jargon exactly as dictated. Format code blocks if detected. Do not translate technical English terms."
}

def get_system_prompt():
    return config_manager.get("custom_system_prompt") or DEFAULT_SYSTEM_PROMPT

def get_presets():
    return config_manager.get("presets") or DEFAULT_PRESETS

def get_current_mode():
    return config_manager.get("current_mode") or "Strict Cleanup"

NOTION_CATEGORIZATION_PROMPT = """You are an AI assistant that structures raw thoughts for a Notion database.
You will be given a text which represents a user's dictated note.
Your task is to analyze the text and output a JSON object with the following fields:
1. "is_useful" (boolean): true if the text seems like a meaningful thought, task, or note. false if it's just garbage, an accident, or a single trailing question with no context.
2. "topic" (string): The overall topic of the note (e.g., "Work", "Ideas", "Personal", "Code", "Random"). Try to keep it to one or two words.
3. "tags" (list of strings): Up to 3 relevant tags.

Your output MUST be ONLY valid JSON and nothing else. Do NOT wrap it in markdown block quotes (` ```json `). Just pure JSON.
"""

# Audio Config
SAMPLE_RATE = 16000
CHANNELS = 1
SILENCE_THRESHOLD_RMS = 0.001  # Tune this based on microphone volume
MIN_AUDIO_DURATION_SEC = 0.2  # FR-1.5: lowered threshold — short words like 'Ok', 'Done' must pass

