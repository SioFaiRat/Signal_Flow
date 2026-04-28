import json
from pathlib import Path

class AppConfig:
    def __init__(self, config_path: str = "config.json"):
        # config.py находится в src/utils/ -> parent.parent.parent = корень проекта
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.path = self.project_root / config_path
        self.data = self._load()
        
    def _load(self) -> dict:
        if not self.path.exists():
            raise FileNotFoundError(
                f"❌ Конфиг не найден: {self.path}\n"
                f"📁 Создай файл config.json в корне проекта (рядом с папкой src/)"
            )
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)
            
    def get(self, *keys, default=None):
        """Безопасный доступ к вложенным ключам: config.get("network", "port")"""
        data = self.data
        for key in keys:
            if isinstance(data, dict) and key in data:
                data = data[key]
            else:
                return default
        return data