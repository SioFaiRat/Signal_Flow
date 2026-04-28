import subprocess
import json
from pathlib import Path

# 1. Получаем список моделей от Ollama
result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
installed_models = set()
for line in result.stdout.splitlines()[1:]:  # Пропускаем заголовок
    name = line.split()[0] if line.strip() else None
    if name:
        installed_models.add(name)

# 2. Читаем конфиг
cfg_path = Path("config.json")
with open(cfg_path, "r", encoding="utf-8") as f:
    config = json.load(f)

model_in_config = config.get("ai", {}).get("default_model")

# 3. Сравниваем
print(f"📦 Установленные модели: {installed_models}")
print(f"📝 В config.json указано: {model_in_config!r}")

if model_in_config in installed_models:
    print("Модель найдена. Всё верно.")
else:
    print("НЕ СОВПАДАЕТ! Исправь 'default_model' в config.json")