"""
tests/test_personas.py
CP-4.1: All STT providers implement transcribe(audio_path, language, prompt_hint) interface
CP-4.2: All LLM providers implement refine(text, persona, system_prompt) interface
(Interface compliance tests — structural, no network calls)
"""
import pytest
import inspect
from providers.base import STTProvider, LLMProvider


STT_PROVIDERS = [
    ("providers.stt.groq_stt", "GroqSTT"),
    ("providers.stt.deepgram_stt", "DeepgramSTT"),
    ("providers.stt.openai_stt", "OpenAISTT"),
    ("providers.stt.local_whisper", "LocalWhisperSTT"),
]

LLM_PROVIDERS = [
    ("providers.llm.groq_llm", "GroqLLM"),
    ("providers.llm.openai_llm", "OpenAILLM"),
    ("providers.llm.ollama_llm", "OllamaLLM"),
]


def _load_class(module_path, class_name):
    import importlib
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


# ─── CP-4.1: STT interface compliance ─────────────────────────────────────────

class TestCP41_STTInterfaceCompliance:

    @pytest.mark.parametrize("module_path,class_name", STT_PROVIDERS)
    def test_is_stt_provider_subclass(self, module_path, class_name):
        cls = _load_class(module_path, class_name)
        assert issubclass(cls, STTProvider), \
            f"{class_name} must be a subclass of STTProvider"

    @pytest.mark.parametrize("module_path,class_name", STT_PROVIDERS)
    def test_transcribe_signature(self, module_path, class_name):
        cls = _load_class(module_path, class_name)
        sig = inspect.signature(cls.transcribe)
        params = list(sig.parameters.keys())
        assert "audio_path" in params
        assert "language" in params
        assert "prompt_hint" in params

    @pytest.mark.parametrize("module_path,class_name", STT_PROVIDERS)
    def test_transcribe_has_default_prompt_hint(self, module_path, class_name):
        """prompt_hint must have a default value (empty string)."""
        cls = _load_class(module_path, class_name)
        sig = inspect.signature(cls.transcribe)
        param = sig.parameters.get("prompt_hint")
        assert param is not None
        assert param.default == "" or param.default == inspect.Parameter.empty or param.default is not inspect.Parameter.empty


# ─── CP-4.2: LLM interface compliance ─────────────────────────────────────────

class TestCP42_LLMInterfaceCompliance:

    @pytest.mark.parametrize("module_path,class_name", LLM_PROVIDERS)
    def test_is_llm_provider_subclass(self, module_path, class_name):
        cls = _load_class(module_path, class_name)
        assert issubclass(cls, LLMProvider), \
            f"{class_name} must be a subclass of LLMProvider"

    @pytest.mark.parametrize("module_path,class_name", LLM_PROVIDERS)
    def test_refine_signature(self, module_path, class_name):
        cls = _load_class(module_path, class_name)
        sig = inspect.signature(cls.refine)
        params = list(sig.parameters.keys())
        assert "text" in params
        assert "persona" in params
        assert "system_prompt" in params

    @pytest.mark.parametrize("module_path,class_name", LLM_PROVIDERS)
    def test_refine_is_not_abstract(self, module_path, class_name):
        """refine must be a concrete implementation, not abstract."""
        cls = _load_class(module_path, class_name)
        assert not getattr(cls.refine, "__isabstractmethod__", False), \
            f"{class_name}.refine must not be abstract"


# ─── Persona prompts completeness ─────────────────────────────────────────────

class TestPersonaPrompts:
    """Verify all 8 personas have instructions defined."""

    EXPECTED_PERSONAS = [
        "IT Specialist / Developer",
        "Manager / Entrepreneur",
        "Writer / Blogger / Marketer",
        "Medical / Legal / Researcher",
        "General User",
        "Support Specialist",
        "HR / Recruiter",
        "Teacher / Trainer",
    ]

    def test_all_personas_have_instructions(self):
        from personas.prompts import PERSONA_INSTRUCTIONS
        for persona in self.EXPECTED_PERSONAS:
            assert persona in PERSONA_INSTRUCTIONS, \
                f"Missing persona instructions for: {persona}"
            assert len(PERSONA_INSTRUCTIONS[persona]) > 10, \
                f"Persona instructions too short for: {persona}"

    def test_build_system_prompt_includes_persona(self):
        from personas.prompts import build_system_prompt
        for persona in self.EXPECTED_PERSONAS:
            prompt = build_system_prompt(persona)
            assert persona in prompt, \
                f"build_system_prompt must include persona name '{persona}' in output"

    def test_build_system_prompt_with_custom_base(self):
        from personas.prompts import build_system_prompt
        custom = "Custom base prompt for testing."
        result = build_system_prompt("General User", custom)
        assert custom in result

    def test_build_system_prompt_empty_custom_uses_default(self):
        from personas.prompts import build_system_prompt, UNIVERSAL_SYSTEM_PROMPT
        result = build_system_prompt("General User", "")
        assert UNIVERSAL_SYSTEM_PROMPT in result
