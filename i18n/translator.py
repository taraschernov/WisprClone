import json
import os
from utils.logger import get_logger

logger = get_logger("yapclean.i18n")

_LOCALES_DIR = os.path.join(os.path.dirname(__file__), "locales")


class Translator:
    def __init__(self, locale: str = "en"):
        self._locale = locale
        self._strings = {}
        self._fallback = {}
        self._load("en")  # always load English as fallback
        if locale != "en":
            self._load(locale)

    def _load(self, locale: str):
        path = os.path.join(_LOCALES_DIR, f"{locale}.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if locale == "en":
                self._fallback = data
            self._strings = data
        except Exception as e:
            logger.warning(f"Could not load locale '{locale}': {e}")

    def set_locale(self, locale: str):
        self._locale = locale
        self._strings = dict(self._fallback)  # reset to English
        if locale != "en":
            self._load(locale)

    def t(self, key: str, **kwargs) -> str:
        template = self._strings.get(key) or self._fallback.get(key, key)
        return template.format(**kwargs) if kwargs else template


# Global singleton — initialized after config is loaded
_translator = Translator("en")


def init_translator(locale: str):
    _translator.set_locale(locale)


def t(key: str, **kwargs) -> str:
    return _translator.t(key, **kwargs)
