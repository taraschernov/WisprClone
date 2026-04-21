import re
from utils.logger import get_logger

logger = get_logger("yapclean.refusal_detector")

REFUSAL_PATTERNS = [
    r"^i'?m sorry\b",
    r"^i am sorry\b",
    r"^as an ai\b",
    r"^i cannot\b",
    r"^i can'?t\b",
    r"^извините,?\s*я не",
    r"^как языковая модель",
    r"^here is your",
    r"^here'?s your",
    r"^вот ваш текст",
    r"^sure[,!]\s",
    r"^of course[,!]\s",
    r"^certainly[,!]\s",
    # Detect LLM answering a question instead of formatting it
    r"^чтобы .{5,}, (выполните|сделайте|перейдите|нажмите|откройте)",
    r"^для (того чтобы|настройки|решения)",
    r"^вот (как|шаги|инструкция|способ)",
    r"^следуйте (этим|следующим)",
    r"^to (configure|set up|fix|solve|enable|disable)\b",
    r"^here are (the steps|instructions|some)",
    r"^follow these",
]


class RefusalDetector:
    def check(self, llm_output: str, fallback: str) -> str:
        text = llm_output.strip()
        text_lower = text.lower()
        for pattern in REFUSAL_PATTERNS:
            if re.match(pattern, text_lower, re.IGNORECASE):
                logger.warning(f"LLM refusal detected (pattern: {pattern}), using raw transcript as fallback")
                return fallback
        return text

