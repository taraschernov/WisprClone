"""
tests/test_providers.py
CP-4.1: All STT providers implement transcribe(audio_path, language, prompt_hint) interface
CP-4.2: All LLM providers implement refine(text, persona, system_prompt) interface
CP-4.3: Fallback chain tries next provider on ProviderError
"""
import pytest
import inspect
from unittest.mock import MagicMock, patch
from hypothesis import given, settings
from hypothesis import strategies as st

from providers.base import STTProvider, LLMProvider, ProviderError


# ─── CP-4.1: All STT providers implement the interface ────────────────────────

class TestCP41_STTInterface:
    """CP-4.1: All STT providers must implement transcribe(audio_path, language, prompt_hint) -> str."""

    STT_PROVIDER_CLASSES = [
        ("providers.stt.groq_stt", "GroqSTT"),
        ("providers.stt.deepgram_stt", "DeepgramSTT"),
        ("providers.stt.openai_stt", "OpenAISTT"),
        ("providers.stt.local_whisper", "LocalWhisperSTT"),
    ]

    @pytest.mark.parametrize("module_path,class_name", STT_PROVIDER_CLASSES)
    def test_stt_provider_is_subclass(self, module_path, class_name):
        """Each STT provider must be a subclass of STTProvider."""
        import importlib
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        assert issubclass(cls, STTProvider), f"{class_name} must subclass STTProvider"

    @pytest.mark.parametrize("module_path,class_name", STT_PROVIDER_CLASSES)
    def test_stt_provider_has_transcribe_method(self, module_path, class_name):
        """Each STT provider must have a transcribe method with correct signature."""
        import importlib
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        assert hasattr(cls, "transcribe"), f"{class_name} must have transcribe method"
        sig = inspect.signature(cls.transcribe)
        params = list(sig.parameters.keys())
        assert "audio_path" in params, f"{class_name}.transcribe must have audio_path param"
        assert "language" in params, f"{class_name}.transcribe must have language param"
        assert "prompt_hint" in params, f"{class_name}.transcribe must have prompt_hint param"


# ─── CP-4.2: All LLM providers implement the interface ────────────────────────

class TestCP42_LLMInterface:
    """CP-4.2: All LLM providers must implement refine(text, persona, system_prompt) -> str."""

    LLM_PROVIDER_CLASSES = [
        ("providers.llm.groq_llm", "GroqLLM"),
        ("providers.llm.openai_llm", "OpenAILLM"),
        ("providers.llm.ollama_llm", "OllamaLLM"),
    ]

    @pytest.mark.parametrize("module_path,class_name", LLM_PROVIDER_CLASSES)
    def test_llm_provider_is_subclass(self, module_path, class_name):
        """Each LLM provider must be a subclass of LLMProvider."""
        import importlib
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        assert issubclass(cls, LLMProvider), f"{class_name} must subclass LLMProvider"

    @pytest.mark.parametrize("module_path,class_name", LLM_PROVIDER_CLASSES)
    def test_llm_provider_has_refine_method(self, module_path, class_name):
        """Each LLM provider must have a refine method with correct signature."""
        import importlib
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        assert hasattr(cls, "refine"), f"{class_name} must have refine method"
        sig = inspect.signature(cls.refine)
        params = list(sig.parameters.keys())
        assert "text" in params, f"{class_name}.refine must have text param"
        assert "persona" in params, f"{class_name}.refine must have persona param"
        assert "system_prompt" in params, f"{class_name}.refine must have system_prompt param"


# ─── CP-4.3: Fallback chain tries next provider on ProviderError ──────────────

class TestCP43_FallbackChain:
    """CP-4.3: Fallback chain must try the next provider when one raises ProviderError."""

    def test_fallback_to_second_provider_on_error(self):
        """When first provider fails, second provider is tried."""
        call_order = []

        class FailingProvider(STTProvider):
            def transcribe(self, audio_path, language, prompt_hint=""):
                call_order.append("failing")
                raise ProviderError("First provider failed")

        class SucceedingProvider(STTProvider):
            def transcribe(self, audio_path, language, prompt_hint=""):
                call_order.append("succeeding")
                return "transcribed text"

        from providers.registry import ProviderRegistry
        registry = ProviderRegistry()

        with patch.object(registry, "get_stt_chain",
                          return_value=[FailingProvider(), SucceedingProvider()]):
            result = registry.transcribe_with_fallback("fake.wav", "Russian", "")

        assert result == "transcribed text"
        assert call_order == ["failing", "succeeding"]

    def test_all_providers_fail_raises_error(self):
        """When all providers fail, ProviderError is raised."""
        class AlwaysFailProvider(STTProvider):
            def transcribe(self, audio_path, language, prompt_hint=""):
                raise ProviderError("Always fails")

        from providers.registry import ProviderRegistry
        registry = ProviderRegistry()

        with patch.object(registry, "get_stt_chain",
                          return_value=[AlwaysFailProvider(), AlwaysFailProvider()]):
            with pytest.raises(ProviderError):
                registry.transcribe_with_fallback("fake.wav", "Russian", "")

    def test_empty_chain_raises_error(self):
        """Empty provider chain raises ProviderError immediately."""
        from providers.registry import ProviderRegistry
        registry = ProviderRegistry()

        with patch.object(registry, "get_stt_chain", return_value=[]):
            with pytest.raises(ProviderError, match="No STT providers configured"):
                registry.transcribe_with_fallback("fake.wav", "Russian", "")

    @given(st.integers(min_value=1, max_value=5))
    @settings(max_examples=20)
    def test_property_fallback_tries_all_before_failing(self, n_failing):
        """Property: fallback chain tries exactly n providers before giving up."""
        call_count = [0]

        class CountingFailProvider(STTProvider):
            def transcribe(self, audio_path, language, prompt_hint=""):
                call_count[0] += 1
                raise ProviderError("fail")

        from providers.registry import ProviderRegistry
        registry = ProviderRegistry()
        chain = [CountingFailProvider() for _ in range(n_failing)]

        with patch.object(registry, "get_stt_chain", return_value=chain):
            with pytest.raises(ProviderError):
                registry.transcribe_with_fallback("fake.wav", "Russian", "")

        assert call_count[0] == n_failing
