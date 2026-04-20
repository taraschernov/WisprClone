import os
import time
from groq import Groq
from providers.base import STTProvider, ProviderError
from storage.keyring_manager import keyring_manager
from utils.logger import get_logger

logger = get_logger("yapclean.stt.groq")
WHISPER_MODEL = "whisper-large-v3"

LANG_MAP = {
    "Russian": "ru",
    "English": "en",
    "English (UK)": "en",
    "Ukrainian": "uk",
    "German": "de",
    "French": "fr",
    "Spanish": "es",
    "Polish": "pl",
    "Italian": "it",
}


class GroqSTT(STTProvider):
    def transcribe(self, audio_path: str, language: str, prompt_hint: str = "") -> str:
        api_key = keyring_manager.get("api_key")
        if not api_key:
            raise ProviderError("Groq API key not configured")
        client = Groq(api_key=api_key)
        lang_code = LANG_MAP.get(language, "ru")

        for attempt in range(3):
            try:
                with open(audio_path, "rb") as f:
                    result = client.audio.transcriptions.create(
                        file=(os.path.basename(audio_path), f.read()),
                        model=WHISPER_MODEL,
                        language=lang_code,
                        prompt=prompt_hint or None,
                        response_format="text",
                    )
                return str(result)
            except Exception as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    raise ProviderError(f"Groq STT failed after 3 attempts: {e}")
