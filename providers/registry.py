from storage.config_manager import config_manager
from storage.keyring_manager import keyring_manager
from providers.base import STTProvider, LLMProvider, ProviderError
from utils.logger import get_logger

logger = get_logger("yapclean.registry")


class ProviderRegistry:
    def get_stt_chain(self) -> list:
        """Returns ordered list of STT providers based on config."""
        providers = []
        stt_provider = config_manager.get("stt_provider", "groq")

        if stt_provider == "deepgram" and keyring_manager.get("deepgram_api_key"):
            from providers.stt.deepgram_stt import DeepgramSTT
            providers.append(DeepgramSTT())
        elif stt_provider == "openai" and keyring_manager.get("openai_api_key"):
            from providers.stt.openai_stt import OpenAISTT
            providers.append(OpenAISTT())
        elif stt_provider == "local":
            from providers.stt.local_whisper import LocalWhisperSTT
            providers.append(LocalWhisperSTT())

        # Always add Groq as fallback if key available
        if keyring_manager.get("api_key"):
            from providers.stt.groq_stt import GroqSTT
            providers.append(GroqSTT())

        return providers

    def get_llm_provider(self) -> LLMProvider:
        llm_provider = config_manager.get("llm_provider", "groq")
        if llm_provider == "openai" and keyring_manager.get("openai_api_key"):
            from providers.llm.openai_llm import OpenAILLM
            return OpenAILLM()
        elif llm_provider == "ollama":
            from providers.llm.ollama_llm import OllamaLLM
            return OllamaLLM()
        # Default: Groq
        from providers.llm.groq_llm import GroqLLM
        return GroqLLM()

    def transcribe_with_fallback(self, audio_path: str, language: str, prompt_hint: str = "") -> str:
        chain = self.get_stt_chain()
        if not chain:
            raise ProviderError("No STT providers configured")
        last_error = None
        for provider in chain:
            try:
                result = provider.transcribe(audio_path, language, prompt_hint)
                return result
            except ProviderError as e:
                logger.warning(f"STT provider {type(provider).__name__} failed: {e}, trying next...")
                last_error = e
        raise ProviderError(f"All STT providers failed. Last error: {last_error}")
