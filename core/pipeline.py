import os
import re
import threading
import time
from storage.config_manager import config_manager
from providers.registry import ProviderRegistry
from personas.prompts import build_system_prompt
from personas.refusal_detector import RefusalDetector
from utils.logger import get_logger
from app_platform.notifications import notify
from i18n.translator import t

logger = get_logger("yapclean.pipeline")

# Known Whisper hallucinations on short/silent audio
_WHISPER_HALLUCINATIONS = {
    "продолжение следует",
    "to be continued",
    "спасибо за просмотр",
    "thanks for watching",
    "подписывайтесь на канал",
    "subscribe to the channel",
    "конец",
    "the end",
    "субтитры добавлены",
    "subtitles by",
    "amara.org",
}

def _is_hallucination(text: str) -> bool:
    """Detect known Whisper hallucinations on short/silent audio."""
    t_lower = text.strip().lower().rstrip('.')
    return t_lower in _WHISPER_HALLUCINATIONS or any(h in t_lower for h in _WHISPER_HALLUCINATIONS)


def _is_short_phrase(text: str, max_words: int = 4) -> bool:
    """Short phrases (<=max_words) should skip LLM to preserve exact words."""
    return len(text.strip().split()) <= max_words


def _format_short_phrase(text: str) -> str:
    """Minimal formatting: capitalize + add period if missing."""
    text = text.strip()
    if not text:
        return text
    text = text[0].upper() + text[1:]
    if text[-1] not in '.!?,;:':
        text += '.'
    return text


def _detect_notion_trigger(text: str, trigger_word: str) -> bool:
    if not trigger_word:
        return False
    trigger_esc = re.escape(trigger_word)
    pattern = re.compile(
        rf'(^[\s\W]*{trigger_esc}\b)|(\b{trigger_esc}[\s\W]*$)', re.IGNORECASE
    )
    return bool(pattern.search(text))


def _remove_trigger_word(text: str, trigger_word: str) -> str:
    pattern_start = re.compile(r'^[\s\W]*' + re.escape(trigger_word) + r'[\s\W]*', re.IGNORECASE)
    pattern_end = re.compile(r'[\s\W]*' + re.escape(trigger_word) + r'[\s\W]*$', re.IGNORECASE)
    if pattern_start.search(text):
        text = pattern_start.sub('', text, count=1).strip()
        if text:
            text = text[0].upper() + text[1:]
    elif pattern_end.search(text):
        text = pattern_end.sub('', text, count=1).strip()
        if text and not text.endswith(('.', '!', '?')):
            text += '.'
    return text


class Pipeline:
    def __init__(self, injector, app_awareness=None, persona_router=None, pill=None):
        self.injector = injector
        self.app_awareness = app_awareness
        self.persona_router = persona_router
        self.pill = pill
        self._registry = ProviderRegistry()
        self._refusal_detector = RefusalDetector()

    def _resolve_persona(self) -> str:
        if self.app_awareness and self.persona_router:
            try:
                process_name = self.app_awareness.get_active_process()
                return self.persona_router.resolve(process_name)
            except Exception:
                pass
        return config_manager.get("active_persona", "General User")

    def process(self, audio_path: str, target_language: str = None) -> None:
        """Full pipeline: STT -> LLM format -> LLM translate (optional) -> Inject -> Notion."""
        start_time = time.time()
        try:
            # 1. Resolve persona and dictation language
            persona = self._resolve_persona()
            dictation_lang = config_manager.get("dictation_language", "Russian")
            logger.info(f"Pipeline start — persona: {persona}, language: {dictation_lang}")

            # 2. STT
            from personas.stt_hints import STT_HINTS
            prompt_hint = STT_HINTS.get(persona, "")
            try:
                raw_text = self._registry.transcribe_with_fallback(audio_path, dictation_lang, prompt_hint)
            except Exception as stt_err:
                logger.error(f"STT failed: {stt_err}")
                notify("YapClean", t("error.stt_failed"), "error")
                return
            logger.info(f"Transcription ({time.time()-start_time:.2f}s): {raw_text}")

            if not raw_text.strip():
                logger.info("Empty transcription, skipping.")
                return

            # Block known Whisper hallucinations
            if _is_hallucination(raw_text):
                logger.warning(f"Whisper hallucination detected, skipping: '{raw_text}'")
                return

            # 3. LLM Smart Formatting
            bypass = config_manager.get("bypass_llm", False)

            if bypass:
                formatted_text = raw_text
                logger.info("Bypass mode: skipping LLM.")
            elif _is_short_phrase(raw_text):
                # Short phrases (<=4 words): skip LLM, preserve exact words
                formatted_text = _format_short_phrase(raw_text)
                logger.info(f"Short phrase ({len(raw_text.split())} words), skipping LLM: '{formatted_text}'")
            else:
                if self.pill:
                    self.pill.set_state("formatting")
                custom_prompt = config_manager.get("custom_system_prompt", "")
                system_prompt = build_system_prompt(persona, custom_prompt)
                llm_provider = self._registry.get_llm_provider()
                try:
                    llm_output = llm_provider.refine(raw_text, persona, system_prompt)
                    # Strip any XML/HTML tags the LLM might have added
                    llm_output = re.sub(r'<[^>]+>', '', llm_output).strip()
                    formatted_text = self._refusal_detector.check(llm_output, fallback=raw_text)
                except Exception as llm_err:
                    logger.error(f"LLM failed: {llm_err}")
                    notify("YapClean", t("error.llm_failed"), "warning")
                    formatted_text = raw_text
                logger.info(f"LLM refined ({time.time()-start_time:.2f}s): {formatted_text}")

            # 4. Translation step (if keyboard layout differs from dictation language)
            final_text = formatted_text
            needs_translation = (
                target_language
                and target_language != dictation_lang
                and "Language ID" not in str(target_language)
                and not bypass
            )
            if needs_translation:
                translate_prompt = (
                    f"Translate the following text to {target_language}. "
                    f"CRITICAL: Preserve the exact structure, formatting, line breaks, bullet points, and dashes from the original. "
                    f"Preserve all technical terms, proper nouns, code snippets, and abbreviations as-is. "
                    f"Output ONLY the translated text, nothing else. "
                    f"Do NOT wrap the output in any tags, brackets, or markup."
                )
                try:
                    llm_provider = self._registry.get_llm_provider()
                    translated = llm_provider.refine(formatted_text, persona, translate_prompt)
                    translated = re.sub(r'<[^>]+>', '', translated).strip()
                    final_text = self._refusal_detector.check(translated, fallback=formatted_text)
                    logger.info(f"Translated ({time.time()-start_time:.2f}s) -> {target_language}: {final_text}")
                except Exception as e:
                    logger.error(f"Translation failed: {e}")
                    final_text = formatted_text

            # 5. Inject
            self.injector.inject_text(final_text)
            logger.info(f"Total pipeline time: {time.time()-start_time:.2f}s")

            # Show done state in pill
            if self.pill:
                self.pill.set_state("done", persona=persona)

            # 6. Notion (optional, non-blocking)
            enable_notion = config_manager.get("enable_notion", False)
            trigger_word = config_manager.get("notion_trigger_word", "")
            if enable_notion:
                should_send = _detect_notion_trigger(raw_text, trigger_word) if trigger_word else True
                if should_send:
                    notion_text = _remove_trigger_word(final_text, trigger_word) if trigger_word else final_text
                    from integrations.notion import categorize_and_send_to_notion
                    threading.Thread(
                        target=categorize_and_send_to_notion,
                        args=(notion_text,),
                        daemon=True
                    ).start()

        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            if self.pill:
                self.pill.set_state("done", error=str(e)[:50])
        finally:
            if os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                except Exception as e:
                    logger.error(f"Failed to delete temp audio file: {e}")
