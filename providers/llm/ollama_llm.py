import time
import requests
from providers.base import LLMProvider, ProviderError
from storage.config_manager import config_manager
from utils.logger import get_logger

logger = get_logger("yapclean.llm.ollama")


class OllamaLLM(LLMProvider):
    def refine(self, text: str, persona: str, system_prompt: str) -> str:
        base_url = config_manager.get("ollama_url", "http://localhost:11434")
        model = config_manager.get("ollama_model", "llama3")

        for attempt in range(3):
            try:
                resp = requests.post(
                    f"{base_url}/api/chat",
                    json={
                        "model": model,
                        "messages": [
                            {
                                "role": "system",
                                "content": f"{system_prompt}\n\nActive Persona: {persona}",
                            },
                            {
                                "role": "user",
                                "content": f"<transcription>\n{text}\n</transcription>",
                            },
                        ],
                        "stream": False,
                    },
                    timeout=60,
                )
                return resp.json()["message"]["content"].strip()
            except Exception as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    raise ProviderError(f"Ollama LLM failed after 3 attempts: {e}")
