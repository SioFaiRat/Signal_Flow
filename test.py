import requests
import json

payload = {
    "model": "phi3:mini",
    "prompt": "Say hello in JSON: {\"msg\":\"hi\"}",
    "stream": False
}

try:
    print("[*] Запрос к Ollama...")
    r = requests.post("http://localhost:11434/api/generate", json=payload, timeout=30)
    print(f"[OK] Статус: {r.status_code}")
    
    data = r.json()
    raw_response = data.get('response', '')
    
    # 🔧 ОЧИСТКА ОТ MARKDOWN
    if "```" in raw_response:
        # Находим JSON между ```json и ```
        raw_response = raw_response.split("```")[-2] if raw_response.count("```") >= 2 else raw_response.replace("```", "")
    
    raw_response = raw_response.strip()
    
    print(f"[OK] Очищенный ответ: {raw_response[:200]}")
    
    # Теперь парсим
    parsed = json.loads(raw_response)
    print(f"[OK] Распарсенный JSON: {parsed}")
    print("[SUCCESS] Всё работает!")
    
except json.JSONDecodeError as je:
    print(f"[ERROR] JSON парсинг упал: {je}")
    print(f"[DEBUG] Сырой ответ: {raw_response}")
    
except Exception as e:
    print(f"[ERROR] {e}")