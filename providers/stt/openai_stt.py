import os
import time
from providers.base import STTProvider, ProviderError
from storage.keyring_manager import keyring_manager
from utils.logger import get_logger

logger = get_logger("yapclean.stt.openai")

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


class OpenAISTT(STTProvider):
    def transcribe(self, audio_path: str, language: str, prompt_hint: str = "") -> str:
        from openai import OpenAI

        api_key = keyring_manager.get("openai_api_key")
        if not api_key:
            raise ProviderError("OpenAI API key not configured")
        client = OpenAI(api_key=api_key)
        lang_code = LANG_MAP.get(language, "ru")

        for attempt in range(3):
            try:
                with open(audio_path, "rb") as f:
                    result = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=f,
                        language=lang_code,
                        prompt=prompt_hint or None,
                    )
                return result.text
            except Exception as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    raise ProviderError(f"OpenAI STT failed after 3 attempts: {e}")
