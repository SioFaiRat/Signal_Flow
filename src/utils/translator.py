"""
SignalFlow Controller - Internationalization Module

Provides translation support for multiple languages.
"""
import json
from pathlib import Path
from typing import Any


class Translator:
    """Translation manager for multi-language support."""

    def __init__(self, lang: str = "ru"):
        """
        Initialize translator with specified language.

        Args:
            lang: Language code (e.g., 'ru', 'en', 'zh').
        """
        self.lang = lang
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.data = self._load(lang)

    def _load(self, lang: str) -> dict[str, Any]:
        """
        Load translations for specified language.

        Args:
            lang: Language code.

        Returns:
            Dictionary of translations.
        """
        i18n_dir = self.project_root / "i18n"
        path = i18n_dir / f"{lang}.json"

        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)

        # Fallback to English
        fallback = i18n_dir / "en.json"
        if fallback.exists():
            with open(fallback, "r", encoding="utf-8") as f:
                return json.load(f)

        return {}

    def set_language(self, lang: str) -> None:
        """
        Change current language and reload translations.

        Args:
            lang: New language code.
        """
        self.lang = lang
        self.data = self._load(lang)

    def t(self, key: str, **kwargs: Any) -> str:
        """
        Translate a key with optional formatting.

        Args:
            key: Translation key.
            **kwargs: Format arguments for the translated string.

        Returns:
            Translated and formatted string.
        """
        text = self.data.get("ui", {}).get(key, key)
        return text.format(**kwargs) if kwargs else text

    def get_available_languages(self) -> list[str]:
        """Return list of available language codes."""
        i18n_dir = self.project_root / "i18n"
        return [f.stem for f in i18n_dir.glob("*.json")]