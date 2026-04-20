from providers.base import STTProvider, ProviderError
from storage.config_manager import config_manager
from utils.logger import get_logger

logger = get_logger("yapclean.stt.local")

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


class LocalWhisperSTT(STTProvider):
    def __init__(self):
        self._model = None

    def _get_model(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel

                model_size = config_manager.get("local_model_size", "base")
                self._model = WhisperModel(model_size, device="cpu", compute_type="int8")
                logger.info(f"Loaded local Whisper model: {model_size}")
            except ImportError:
                raise ProviderError(
                    "faster-whisper not installed. Run: pip install faster-whisper"
                )
        return self._model

    def transcribe(self, audio_path: str, language: str, prompt_hint: str = "") -> str:
        try:
            model = self._get_model()
            lang_code = LANG_MAP.get(language, "ru")
            segments, _ = model.transcribe(
                audio_path,
                language=lang_code,
                initial_prompt=prompt_hint or None,
            )
            return " ".join(s.text for s in segments).strip()
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(f"Local Whisper failed: {e}")
