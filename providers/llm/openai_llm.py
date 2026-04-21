import time
from providers.base import LLMProvider, ProviderError
from storage.keyring_manager import keyring_manager
from utils.logger import get_logger

logger = get_logger("yapclean.llm.openai")


class OpenAILLM(LLMProvider):
    def refine(self, text: str, persona: str, system_prompt: str) -> str:
        from openai import OpenAI

        api_key = keyring_manager.get("openai_api_key")
        if not api_key:
            raise ProviderError("OpenAI API key not configured")
        client = OpenAI(api_key=api_key)

        for attempt in range(3):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": f"{system_prompt}\n\nActive Persona: {persona}",
                        },
                        {
                            "role": "user",
                            "content": text,
                        },
                    ],
                    max_tokens=2048,
                    temperature=0.3,
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    raise ProviderError(f"OpenAI LLM failed after 3 attempts: {e}")

