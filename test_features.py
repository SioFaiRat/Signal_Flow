"""Тест новых функций: кнопка запуска Ollama и окно дебага"""
import sys
from PyQt6.QtWidgets import QApplication
from src.gui.main_window import MainWindow, DebugWindow, OllamaMonitor

def test_all():
    app = QApplication(sys.argv)
    
    print("=" * 50)
    print("ТЕСТ 1: Создание MainWindow")
    print("=" * 50)
    window = MainWindow()
    assert hasattr(window, 'ollama_btn'), "Нет кнопки ollama_btn"
    assert hasattr(window, 'debug_btn'), "Нет кнопки debug_btn"
    assert hasattr(window, 'ollama_monitor'), "Нет ollama_monitor"
    assert hasattr(window, 'debug_window'), "Нет debug_window"
    print("✅ Все атрибуты MainWindow на месте")
    
    print()
    print("=" * 50)
    print("ТЕСТ 2: Кнопка запуска Ollama")
    print("=" * 50)
    assert window.ollama_btn.text() == "🦙 Запуск Ollama", "Неверный текст кнопки"
    assert window.ollama_status_label.text() == "⚪ Ollama: Не активен", "Неверный статус"
    print(f"   Текст кнопки: {window.ollama_btn.text()}")
    print(f"   Текст статуса: {window.ollama_status_label.text()}")
    print("✅ Кнопка Ollama корректна")
    
    print()
    print("=" * 50)
    print("ТЕСТ 3: Сигналы OllamaMonitor")
    print("=" * 50)
    window._on_ollama_status_changed(True, "Ollama работает")
    assert window.ollama_btn.text() == "🛑 Остановить Ollama", "Кнопка не изменилась при запуске"
    assert "🟢" in window.ollama_status_label.text(), "Статус не стал зелёным"
    print(f"   После запуска: {window.ollama_btn.text()}")
    print(f"   Статус: {window.ollama_status_label.text()}")
    
    window._on_ollama_status_changed(False, "Ollama остановлен")
    assert window.ollama_btn.text() == "🦙 Запуск Ollama", "Кнопка не изменилась при остановке"
    print(f"   После остановки: {window.ollama_btn.text()}")
    print("✅ Сигналы работают корректно")
    
    print()
    print("=" * 50)
    print("ТЕСТ 4: Окно отладки DebugWindow")
    print("=" * 50)
    debug_win = DebugWindow(window)
    assert hasattr(debug_win, 'ollama_status'), "Нет статуса Ollama"
    assert hasattr(debug_win, 'server_status'), "Нет статуса сервера"
    assert hasattr(debug_win, 'model_status'), "Нет статуса модели"
    assert hasattr(debug_win, 'debug_log'), "Нет лога"
    print(f"   Статус Ollama: {debug_win.ollama_status.text()[:50]}...")
    print(f"   Статус TCP: {debug_win.server_status.text()}")
    print("✅ DebugWindow создан корректно")
    
    print()
    print("=" * 50)
    print("ТЕСТ 5: Логирование в DebugWindow")
    print("=" * 50)
    debug_win._log_event("Тестовое событие 1")
    debug_win._log_event("Тестовое событие 2")
    log_text = debug_win.debug_log.toPlainText()
    assert "Тестовое событие 1" in log_text, "Лог 1 не записан"
    assert "Тестовое событие 2" in log_text, "Лог 2 не записан"
    print(f"   Лог содержит {log_text.count('Тестовое событие')} записи")
    print("✅ Логирование работает")
    
    print()
    print("=" * 50)
    print("ТЕСТ 6: Метод открытия окна отладки")
    print("=" * 50)
    assert hasattr(window, '_open_debug_window'), "Нет метода _open_debug_window"
    assert hasattr(window, '_toggle_ollama'), "Нет метода _toggle_ollama"
    print("✅ Методы управления на месте")
    
    print()
    print("=" * 50)
    print("ВСЕ ТЕСТЫ ПРОЙДЕНУ ✅")
    print("=" * 50)
    print()
    print("Новые функции:")
    print("  🦙 Кнопка запуска/остановки Ollama в главном окне")
    print("  🔍 Кнопка открытия окна отладки")
    print("  📊 DebugWindow с мониторингом процессов (Ollama, TCP, Модель)")
    print("  📝 Логирование событий в реальном времени")
    print("  🔄 Автообновление статуса каждые 5 секунд")

if __name__ == "__main__":
    test_all()
