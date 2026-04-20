import time
import requests
from providers.base import STTProvider, ProviderError
from storage.keyring_manager import keyring_manager
from utils.logger import get_logger

logger = get_logger("yapclean.stt.deepgram")

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


class DeepgramSTT(STTProvider):
    def transcribe(self, audio_path: str, language: str, prompt_hint: str = "") -> str:
        api_key = keyring_manager.get("deepgram_api_key")
        if not api_key:
            raise ProviderError("Deepgram API key not configured")
        lang_code = LANG_MAP.get(language, "ru")
        url = (
            f"https://api.deepgram.com/v1/listen"
            f"?model=nova-3&smart_format=true&punctuate=true&language={lang_code}"
        )

        for attempt in range(3):
            try:
                with open(audio_path, "rb") as f:
                    resp = requests.post(
                        url,
                        headers={
                            "Authorization": f"Token {api_key}",
                            "Content-Type": "audio/wav",
                        },
                        data=f,
                        timeout=30,
                    )
                data = resp.json()
                return data["results"]["channels"][0]["alternatives"][0]["transcript"]
            except Exception as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    raise ProviderError(f"Deepgram STT failed after 3 attempts: {e}")
