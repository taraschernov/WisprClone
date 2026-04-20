import time
from groq import Groq
from providers.base import LLMProvider, ProviderError
from storage.keyring_manager import keyring_manager
from utils.logger import get_logger

logger = get_logger("yapclean.llm.groq")
LLM_MODEL = "llama-3.1-8b-instant"


class GroqLLM(LLMProvider):
    def refine(self, text: str, persona: str, system_prompt: str) -> str:
        api_key = keyring_manager.get("api_key")
        if not api_key:
            raise ProviderError("Groq API key not configured")
        client = Groq(api_key=api_key)

        for attempt in range(3):
            try:
                response = client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": f"{system_prompt}\n\nActive Persona: {persona}",
                        },
                        {
                            "role": "user",
                            "content": f"<transcription>\n{text}\n</transcription>",
                        },
                    ],
                    model=LLM_MODEL,
                    max_tokens=2048,
                    temperature=0.3,
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    raise ProviderError(f"Groq LLM failed after 3 attempts: {e}")
