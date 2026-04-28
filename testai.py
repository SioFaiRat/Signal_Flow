import requests
import json

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "phi3:mini"  # ← как в config.json

prompt = "Classify: STATUS: ONLINE; BATTERY=87%. Reply JSON only: {\"classification\": \"NORMAL\"}"

payload = {
    "model": MODEL,
    "prompt": prompt,
    "stream": False,  # ← критично!
    "options": {"temperature": 0.0, "num_predict": 100}
}

try:
    print(f"[*] Запрос к {MODEL}...")
    response = requests.post(OLLAMA_URL, json=payload, timeout=30)
    response.raise_for_status()
    result = response.json()
    print(f"[OK] Ответ: {result.get('response', 'Пусто')[:200]}")
except Exception as e:
    print(f"[ERROR] Ошибка: {e}")