from abc import ABC, abstractmethod


class ProviderError(Exception):
    pass


class STTProvider(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str, language: str, prompt_hint: str = "") -> str:
        """Returns raw transcript. Raises ProviderError on failure."""


class LLMProvider(ABC):
    @abstractmethod
    def refine(self, text: str, persona: str, system_prompt: str) -> str:
        """Returns refined text. Raises ProviderError on failure."""
