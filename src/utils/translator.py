import json
from pathlib import Path

class Translator:
    def __init__(self, lang: str = "ru"):
        self.lang = lang
        # src/utils/translator.py -> parent(3) = корень проекта (SignalFlow/)
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.data = self._load(lang)
        
    def _load(self, lang: str) -> dict:
        i18n_dir = self.project_root / "i18n"
        path = i18n_dir / f"{lang}.json"
        
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
                
        # Fallback на английский
        fallback = i18n_dir / "en.json"
        if fallback.exists():
            with open(fallback, "r", encoding="utf-8") as f:
                return json.load(f)
                
        # Если нет ни ru, ни en — возвращаем пустой словарь, чтобы не крашиться
        return {}
            
    def set_language(self, lang: str):
        self.lang = lang
        self.data = self._load(lang)
        
    def t(self, key: str, **kwargs) -> str:
        text = self.data.get("ui", {}).get(key, key)
        return text.format(**kwargs) if kwargs else text