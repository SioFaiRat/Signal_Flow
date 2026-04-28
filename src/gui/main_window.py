import sys
import io
import socket
import threading
import platform
import json
import subprocess
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from http.server import HTTPServer, SimpleHTTPRequestHandler
import webbrowser
import time


if sys.platform == "win32": # Принудительно устанавливаем UTF-8 для консоли Windows
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QPushButton, QLabel, QComboBox, QPlainTextEdit, QFrame,
                             QDialog, QTextEdit, QSplitter, QMessageBox)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread
from PyQt6.QtGui import QFont

# Предполагаем, что эти модули находятся в вашем проекте
# Если пути отличаются, подкорректируйте импорт
try:
    from src.utils.config import AppConfig
    from src.utils.translator import Translator
    from src.core.process_mgr import ProcessManager
except ImportError:
    # Заглушки для автономного запуска, если модули не найдены
    class AppConfig:
        def get(self, *args, **kwargs): return kwargs.get('default', '127.0.0.1')
    class Translator:
        def __init__(self, lang): self.lang = lang
        def t(self, key, **kwargs): return kwargs.get('default', key)
        def set_language(self, lang): self.lang = lang
    class ProcessManager:
        def stop(self, *args, **kwargs): pass
        class Signal:
            def connect(self, func): pass
        log_line = Signal()
        error_occurred = Signal()
        process_started = Signal()
        process_stopped = Signal()

class TestTCPServer:
    """Встроенный тестовый TCP сервер для приема данных с веб-интерфейсом"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 9998, web_port: int = 8080):
        self.host = host
        self.port = port
        self.web_port = web_port
        self._socket: Optional[socket.socket] = None
        self._web_server: Optional[HTTPServer] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._web_thread: Optional[threading.Thread] = None
        self._message_count = 0
        self._last_message: str = ""
        self._last_time: str = ""
        self._received_data: List[Dict[str, str]] = []
        self._lock = threading.Lock()
        self._max_history = 100
        
    def start(self) -> bool:
        """Запуск сервера"""
        try:
            # Запуск TCP сервера
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.bind((self.host, self.port))
            self._socket.listen(5)
            self._running = True
            
            self._thread = threading.Thread(target=self._accept_connections, daemon=True)
            self._thread.start()
            
            # Запуск Веб сервера
            self._web_server = HTTPServer((self.host, self.web_port), WebHandler)
            WebHandler.server_instance = self
            self._web_thread = threading.Thread(target=self._web_server.serve_forever, daemon=True)
            self._web_thread.start()
            
            print(f"[+] Test Server started on {self.host}:{self.port}")
            print(f"[+] Web Interface available at http://{self.host}:{self.web_port}")
            return True
        except Exception as e:
            print(f"[!] Test Server start error: {e}")
            return False
    
    def _accept_connections(self):
        """Прием подключений"""
        while self._running and self._socket:
            try:
                conn, addr = self._socket.accept()
                thread = threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True)
                thread.start()
            except OSError:
                break
    
    def _handle_client(self, conn: socket.socket, addr: tuple):
        """Обработка клиента - УЛУЧШЕННАЯ ВЕРСИЯ"""
        with conn:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Connected: {addr[0]}:{addr[1]}")
            try:
                # Читаем данные порциями пока клиент не закроет соединение
                chunks = []
                conn.settimeout(3.0)  # Таймаут 3 секунды
                while True:
                    try:
                        chunk = conn.recv(4096)
                        if not chunk:
                            break
                        chunks.append(chunk)
                    except socket.timeout:
                        break
                
                if chunks:
                    message = b''.join(chunks).decode('utf-8', errors='replace').strip()
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    
                    with self._lock:
                        self._message_count += 1
                        self._last_message = message
                        self._last_time = timestamp
                        
                        entry = {
                            "time": timestamp,
                            "data": message,
                            "source": f"{addr[0]}:{addr[1]}",
                            "id": self._message_count
                        }
                        self._received_data.insert(0, entry)
                        if len(self._received_data) > self._max_history:
                            self._received_data.pop()
                    
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Received #{self._message_count}: {message[:100]}...")
                    
                    # Отправляем подтверждение клиенту
                    response = f"OK: Received {self._message_count} messages at {timestamp}\n"
                    conn.sendall(response.encode('utf-8'))
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Sent confirmation to client")
            except Exception as e:
                print(f"[!] Client error: {e}")
    
    def stop(self):
        """Остановка сервера"""
        self._running = False
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None
        if self._web_server:
            try:
                self._web_server.shutdown()
            except Exception:
                pass
        print("[-] Test Server stopped")
    
    @property
    def message_count(self) -> int:
        return self._message_count
    
    @property
    def last_message(self) -> str:
        return self._last_message
    
    @property
    def last_time(self) -> str:
        return self._last_time
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    @property
    def received_data(self) -> List[Dict[str, str]]:
        with self._lock:
            return list(self._received_data)


class WebHandler(SimpleHTTPRequestHandler):
    """Веб-обработчик для отображения полученных данных"""
    server_instance: Optional[TestTCPServer] = None
    
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
            html = self.generate_html()
            self.wfile.write(html.encode('utf-8'))
        elif self.path == '/api/data':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            
            if self.server_instance:
                data = json.dumps(self.server_instance.received_data, ensure_ascii=False)
            else:
                data = "[]"
            self.wfile.write(data.encode('utf-8'))
        else:
            super().do_GET()
    
    def generate_html(self):
        rows = ""
        if self.server_instance:
            for item in self.server_instance.received_data:
                safe_data = item['data'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')
                rows += f"""
                <tr>
                    <td>{item['time']}</td>
                    <td>{item['source']}</td>
                    <td style="font-family: monospace; white-space: pre-wrap;">{safe_data}</td>
                </tr>
                """
        
        html = f"""
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <title>SignalFlow Monitor</title>
            <meta http-equiv="refresh" content="2">
            <style>
                body {{ font-family: sans-serif; background: #f0f2f5; padding: 20px; }}
                h1 {{ color: #333; }}
                table {{ width: 100%; border-collapse: collapse; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.2); }}
                th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #007bff; color: white; }}
                tr:hover {{ background-color: #f1f1f1; }}
                .status {{ color: green; font-weight: bold; }}
                .empty {{ text-align: center; color: #888; padding: 20px; }}
            </style>
        </head>
        <body>
            <h1>📡 SignalFlow Monitor</h1>
            <p>Статус сервера: <span class="status">● Активен</span> (Порт 9998)</p>
            <p>Автообновление: 2 сек. <a href="/api/data" target="_blank">JSON API</a></p>
            <table>
                <thead>
                    <tr>
                        <th width="10%">Время</th>
                        <th width="20%">Источник</th>
                        <th>Данные</th>
                    </tr>
                </thead>
                <tbody>
                    {rows if rows else '<tr><td colspan="3" class="empty">Ожидание данных...</td></tr>'}
                </tbody>
            </table>
        </body>
        </html>
        """
        return html


class OllamaMonitor(QObject):
    """Монитор состояния Ollama"""
    status_changed = pyqtSignal(bool, str)  # is_running, message
    
    def __init__(self):
        super().__init__()
        self.is_running = False
        self.process: subprocess.Popen | None = None
        self._check_timer = QTimer()
        self._check_timer.timeout.connect(self._check_status)
        
    def start_ollama(self, config_path: str = "config.json"):
        """Запуск ollama serve"""
        if self.is_running and self.process and self.process.poll() is None:
            return False, "Ollama уже запущен"
        
        try:
            # Запускаем ollama serve без окна консоли на Windows
            creationflags = 0
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NO_WINDOW
            
            self.process = subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=creationflags
            )
            
            # Поток для чтения логов
            threading.Thread(target=self._read_ollama_logs, daemon=True).start()
            
            self.is_running = True
            self.status_changed.emit(True, "Ollama запущен")
            return True, "Ollama запущен успешно"
        except FileNotFoundError:
            return False, "Ollama не найден. Установите Ollama."
        except Exception as e:
            return False, f"Ошибка запуска: {e}"
    
    def stop_ollama(self):
        """Остановка ollama"""
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            except Exception as e:
                return False, f"Ошибка остановки: {e}"
        
        self.is_running = False
        self.process = None
        self.status_changed.emit(False, "Ollama остановлен")
        return True, "Ollama остановлен"
    
    def _read_ollama_logs(self):
        """Чтение логов Ollama в фоновом потоке"""
        if self.process and self.process.stdout:
            for line in iter(self.process.stdout.readline, ""):
                if line:
                    # Отправляем логи в главный поток через сигнал
                    pass  # Можно добавить сигнал для логов
    
    def _check_status(self):
        """Проверка доступности Ollama API"""
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                if not self.is_running:
                    self.is_running = True
                    self.status_changed.emit(True, "Ollama доступен")
            else:
                if self.is_running:
                    self.is_running = False
                    self.status_changed.emit(False, "Ollama недоступен")
        except:
            if self.is_running:
                self.is_running = False
                self.status_changed.emit(False, "Ollama недоступен")


class DebugWindow(QDialog):
    """Окно отладки для просмотра процессов и логов"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔍 Дебаг - Мониторинг процессов")
        self.resize(800, 600)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint)
        
        layout = QVBoxLayout(self)
        
        # Статус процессов
        status_group = QGroupBox("📊 Статус процессов")
        status_layout = QVBoxLayout(status_group)
        
        self.ollama_status = QLabel("⚪ Ollama: Не проверялся")
        self.ollama_status.setFont(QFont("Consolas", 11))
        self.server_status = QLabel("⚪ TCP Сервер: Не проверялся")
        self.server_status.setFont(QFont("Consolas", 11))
        self.model_status = QLabel("⚪ Модель: Не проверялась")
        self.model_status.setFont(QFont("Consolas", 11))
        
        status_layout.addWidget(self.ollama_status)
        status_layout.addWidget(self.server_status)
        status_layout.addWidget(self.model_status)
        
        layout.addWidget(status_group)
        
        # Логи
        log_group = QGroupBox("📝 Логи событий")
        log_layout = QVBoxLayout(log_group)
        
        self.debug_log = QTextEdit()
        self.debug_log.setReadOnly(True)
        self.debug_log.setFont(QFont("Consolas", 10))
        self.debug_log.setMinimumHeight(300)
        
        log_layout.addWidget(self.debug_log)
        layout.addWidget(log_group)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("🔄 Обновить статус")
        self.refresh_btn.clicked.connect(self._refresh_all_status)
        self.clear_log_btn = QPushButton("🗑️ Очистить логи")
        self.clear_log_btn.clicked.connect(lambda: self.debug_log.clear())
        
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.clear_log_btn)
        
        layout.addLayout(btn_layout)
        
        # Таймер автообновления
        self.auto_refresh_timer = QTimer()
        self.auto_refresh_timer.timeout.connect(self._refresh_all_status)
        self.auto_refresh_timer.start(5000)  # Каждые 5 секунд
        
        self._log_event("Окно отладки открыто")
        self._refresh_all_status()
    
    def _log_event(self, message: str):
        """Добавление события в лог"""
        timestamp = QTimer().property("current_time") or ""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.debug_log.append(f"[{timestamp}] {message}")
    
    def _refresh_all_status(self):
        """Обновление статуса всех компонентов"""
        # Проверка Ollama
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m["name"] for m in models[:5]]
                self.ollama_status.setText(f"🟢 Ollama: Работает (моделей: {len(models)})")
                self.ollama_status.setStyleSheet("color: #4CAF50;")
                if model_names:
                    self.model_status.setText(f"🟢 Модель: Доступны {', '.join(model_names)}")
                    self.model_status.setStyleSheet("color: #4CAF50;")
                else:
                    self.model_status.setText("🟡 Модель: Нет загруженных моделей")
                    self.model_status.setStyleSheet("color: #FF9800;")
            else:
                raise Exception("API вернул ошибку")
        except Exception as e:
            self.ollama_status.setText(f"🔴 Ollama: Не доступен ({e})")
            self.ollama_status.setStyleSheet("color: #F44336;")
            self.model_status.setText("🔴 Модель: Ollama не работает")
            self.model_status.setStyleSheet("color: #F44336;")
        
        # Проверка TCP сервера
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 9999))
        sock.close()
        if result == 0:
            self.server_status.setText("🟢 TCP Сервер: Порт 9999 открыт")
            self.server_status.setStyleSheet("color: #4CAF50;")
        else:
            self.server_status.setText("🔴 TCP Сервер: Порт 9999 закрыт")
            self.server_status.setStyleSheet("color: #F44336;")
        
        self._log_event("Статус процессов обновлён")


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.config = AppConfig()
        self.tr = Translator(self.config.get("ui", "default_language", default="ru"))
        self.process_mgr = ProcessManager()
        self.ollama_monitor = OllamaMonitor()
        self.test_server = TestTCPServer(host="127.0.0.1", port=9998)  # Встроенный тестовый сервер
        self.debug_window: DebugWindow | None = None
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        self.setWindowTitle(self.tr.t("app_title", default="T-Invest News Hub"))
        self.resize(980, 820)
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # === ВЕРХНЯЯ ПАНЕЛЬ ===
        top_bar = QHBoxLayout()
        self.lang_combo = QComboBox()
        for lang in self.config.get("ui", "available_languages", default=["ru", "en", "zh"]):
            self.lang_combo.addItem(lang.upper(), lang)
        self.lang_combo.setCurrentText(self.tr.lang.upper())
        self.lang_combo.currentTextChanged.connect(self._on_lang_change)
        top_bar.addWidget(QLabel("🌐"))
        top_bar.addWidget(self.lang_combo)
        
        # Кнопка запуска Ollama
        self.ollama_btn = QPushButton("🦙 Запуск Ollama")
        self.ollama_btn.clicked.connect(self._toggle_ollama)
        self.ollama_status_label = QLabel("⚪ Ollama: Не активен")
        self.ollama_status_label.setFont(QFont("Segoe UI", 10))
        top_bar.addWidget(self.ollama_btn)
        top_bar.addWidget(self.ollama_status_label)
        
        # Кнопка запуска тестового сервера
        self.test_server_btn = QPushButton("🖥️ Тестовый сервер")
        self.test_server_btn.setCheckable(True)
        self.test_server_btn.clicked.connect(self._toggle_test_server)
        self.test_server_status = QLabel("⚪ Сервер: Выключен")
        self.test_server_status.setFont(QFont("Segoe UI", 10))
        top_bar.addWidget(self.test_server_btn)
        top_bar.addWidget(self.test_server_status)
        
        # Кнопка отладки
        self.debug_btn = QPushButton("🔍 Дебаг")
        self.debug_btn.clicked.connect(self._open_debug_window)
        top_bar.addStretch()
        
        self.model_label = QLabel(self.tr.t("model_active", model=self.config.get("ai", "default_model", default="phi3:mini")))
        top_bar.addWidget(self.model_label)
        main_layout.addLayout(top_bar)

        # === PIPELINE ВИЗУАЛИЗАЦИЯ ===
        pipe_group = QGroupBox(self.tr.t("pipeline_group", default="🔗 Pipeline Visualization"))
        pipe_layout = QHBoxLayout(pipe_group)
        pipe_layout.setSpacing(25)

        self.node_sender = self._create_node("📤", "Sender", "idle")
        self.node_ai = self._create_node("⚙️", "AI Core", "idle")
        self.node_receiver = self._create_node("📱", "Receiver", "idle")

        pipe_layout.addWidget(self.node_sender, 1)
        pipe_layout.addWidget(self.node_ai, 1)
        pipe_layout.addWidget(self.node_receiver, 1)
        main_layout.addWidget(pipe_group)

        # === КНОПКИ УПРАВЛЕНИЯ ===
        btn_layout = QHBoxLayout()
        
        self.send_btn = QPushButton("📤 Отправить сообщение")
        self.direct_send_btn = QPushButton("⚡ Прямая отправка (без ИИ)")
        self.pc_status_btn = QPushButton("💻 Отправить статус ПК")
        self.emergency_btn = QPushButton("🔴 ЭКСТРЕННАЯ ОСТАНОВКА")
        self.emergency_btn.setObjectName("emergencyBtn")

        btn_layout.addWidget(self.send_btn)
        btn_layout.addWidget(self.direct_send_btn)
        btn_layout.addWidget(self.pc_status_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.emergency_btn)
        main_layout.addLayout(btn_layout)

        # === ПОЛЕ ВВОДА ===
        msg_group = QGroupBox("📝 Ввод данных")
        msg_layout = QVBoxLayout(msg_group)
        self.message_input = QPlainTextEdit()
        self.message_input.setPlaceholderText("Введите сообщение для отправки...")
        self.message_input.setMinimumHeight(60)
        self.message_input.setPlainText("STATUS: ONLINE; BATTERY=87%; SIGNAL=4G")
        msg_layout.addWidget(self.message_input)
        main_layout.addWidget(msg_group)

        # === ЛОГ И СТАТУС ===
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setMinimumHeight(220)
        main_layout.addWidget(self.log_text)

        self.delivery_status = QLabel("📡 Готов к работе")
        self.delivery_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.delivery_status.setObjectName("statusLabel")
        main_layout.addWidget(self.delivery_status)

    def _create_node(self, icon: str, title: str, state: str = "idle"):
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setProperty("class", f"node {state}")
        layout = QVBoxLayout(frame)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(4)

        lbl_icon = QLabel(icon)
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setFont(QFont("Segoe UI Emoji", 28))

        lbl_title = QLabel(title)
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))

        lbl_status = QLabel("Ожидание")
        lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_status.setProperty("class", "status-text")
        lbl_status.setFont(QFont("Segoe UI", 9))

        layout.addWidget(lbl_icon)
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_status)

        frame.lbl_status = lbl_status
        return frame

    def _connect_signals(self):
        self.send_btn.clicked.connect(lambda: self._trigger_send(self.message_input.toPlainText().strip(), self.send_btn, use_ai=True))
        self.direct_send_btn.clicked.connect(lambda: self._trigger_send(self.message_input.toPlainText().strip(), self.direct_send_btn, use_ai=False))
        self.pc_status_btn.clicked.connect(lambda: self._trigger_send(self._get_pc_status(), self.pc_status_btn, use_ai=False))
        self.emergency_btn.clicked.connect(self._emergency_stop)

        self.process_mgr.log_line.connect(self._log)
        self.process_mgr.error_occurred.connect(lambda s, e: self._log(f"[❌ {s}] {e}"))
        self.process_mgr.process_started.connect(lambda n: self._update_node("node_ai", "active", "Обработка..."))
        self.process_mgr.process_stopped.connect(lambda n: self._update_node("node_ai", "idle", "Остановлен"))
        
        # Сигналы от монитора Ollama
        self.ollama_monitor.status_changed.connect(self._on_ollama_status_changed)

    def _toggle_ollama(self):
        """Переключение состояния Ollama"""
        if self.ollama_monitor.is_running:
            success, msg = self.ollama_monitor.stop_ollama()
        else:
            success, msg = self.ollama_monitor.start_ollama()
        
        self._log(f"[Ollama] {msg}")
        if not success:
            self._log(f"[Ollama ERROR] {msg}")

    def _on_ollama_status_changed(self, is_running: bool, message: str):
        """Обновление статуса Ollama в UI"""
        if is_running:
            self.ollama_status_label.setText(f"🟢 {message}")
            self.ollama_status_label.setStyleSheet("color: #4CAF50;")
            self.ollama_btn.setText("🛑 Остановить Ollama")
        else:
            self.ollama_status_label.setText(f"⚪ {message}")
            self.ollama_status_label.setStyleSheet("color: #F44336;")
            self.ollama_btn.setText("🦙 Запуск Ollama")

    def _toggle_test_server(self):
        """Переключение состояния тестового сервера"""
        if self.test_server_btn.isChecked():
            if self.test_server.start():
                self.test_server_status.setText(f"🟢 Сервер: 127.0.0.1:9998")
                self.test_server_status.setStyleSheet("color: #4CAF50;")
                self.test_server_btn.setText("🛑 Остановить сервер")
                self._log("[TestServer] Запущен на 127.0.0.1:9998")
                self._log(f"[TestServer] Web-интерфейс: http://127.0.0.1:{self.test_server.web_port}")
                
                # Автоматически открываем браузер с веб-интерфейсом
                try:
                    webbrowser.open(f"http://127.0.0.1:{self.test_server.web_port}", new=2)
                    self._log("[TestServer] Открыт веб-интерфейс в браузере")
                except Exception as e:
                    self._log(f"[TestServer] Не удалось открыть браузер: {e}")
            else:
                self.test_server_btn.setChecked(False)
                self.test_server_status.setText("🔴 Сервер: Ошибка запуска")
                self.test_server_status.setStyleSheet("color: #F44336;")
                self._log("[TestServer ERROR] Не удалось запустить")
        else:
            self.test_server.stop()
            self.test_server_status.setText("⚪ Сервер: Выключен")
            self.test_server_status.setStyleSheet("")
            self.test_server_btn.setText("🖥️ Тестовый сервер")
            self._log("[TestServer] Остановлен")

    def _open_debug_window(self):
        """Открытие окна отладки"""
        if self.debug_window is None or not self.debug_window.isVisible():
            self.debug_window = DebugWindow(self)
            # Перенаправляем логи из основного окна в дебаг
            self.process_mgr.log_line.connect(lambda src, msg: self.debug_window._log_event(f"[{src}] {msg}") if self.debug_window else None)
        self.debug_window.show()
        self.debug_window.raise_()
        self.debug_window.activateWindow()

    def _trigger_send(self, message: str, btn: QPushButton, use_ai: bool):
        """Запуск отправки данных - УЛУЧШЕННАЯ ВЕРСИЯ"""
        if not message:
            self._log("[!] Нет данных для отправки")
            return

        btn.setEnabled(False)
        
        # Всегда используем встроенный тестовый сервер если он запущен (порт 9998)
        # Это гарантирует что данные будут получены и отображены в веб-интерфейсе
        if self.test_server_btn.isChecked() and self.test_server.is_running:
            ip = "127.0.0.1"
            port = 9998
            self._log(f"[✅ TestServer] Отправка на встроенный сервер {ip}:{port}...")
            self._log(f"[ℹ️] Веб-интерфейс: http://127.0.0.1:{self.test_server.web_port}")
        else:
            ip = self.config.get("network", "simulator_host", default="127.0.0.1")
            port = int(self.config.get("network", "simulator_port", default=9999))
            self._log(f"[⚠️ External] Отправка на внешний сервер {ip}:{port}...")
            self._log(f"[❗] Тестовый сервер выключен! Данные могут не дойти.")

        if use_ai:
            self._log(f"[AI] Подготовка через ИИ-модуль...")
            self._update_node("node_sender", "active", "В очереди ИИ...")
            threading.Thread(target=self._ai_send_worker, args=(ip, port, message, btn), daemon=True).start()
        else:
            self._log(f"[DIRECT] Прямая отправка...")
            self._update_node("node_sender", "active", "Отправка...")
            threading.Thread(target=self._direct_send_worker, args=(ip, port, message, btn), daemon=True).start()

    def _direct_send_worker(self, ip, port, message, btn):
        """Прямая отправка данных без ИИ - УЛУЧШЕННАЯ ВЕРСИЯ"""
        def local_log(msg): 
            QTimer.singleShot(0, lambda: self._log(f"[DIRECT] {msg}"))
        
        try:
            local_log(f"Начало потока. Цель: {ip}:{port}")
            local_log(f"Сообщение: {message[:80]}...")
            QTimer.singleShot(0, lambda: self._update_node("node_receiver", "active", "Соединение..."))
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(10.0)  # Увеличенный таймаут
                s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                
                local_log("Попытка установить TCP-соединение...")
                s.connect((ip, port))
                local_log(f"✅ Соединение с {ip}:{port} установлено успешно.")
                
                # Формируем пакет данных с явным окончанием
                data_to_send = (message + "\n").encode('utf-8')
                local_log(f"Отправка {len(data_to_send)} байт данных...")
                
                # Используем sendall для гарантии отправки всех данных
                s.sendall(data_to_send)
                local_log("✅ Данные ушли в сокет полностью.")
                
                local_log("Ожидание ответа от сервера...")
                # Читаем ответ порциями
                response_chunks = []
                s.settimeout(5.0)
                while True:
                    try:
                        chunk = s.recv(4096)
                        if not chunk:
                            break
                        response_chunks.append(chunk)
                        if len(chunk) < 4096:
                            break
                    except socket.timeout:
                        break
                
                if response_chunks:
                    resp_text = b''.join(response_chunks).decode('utf-8', errors='replace').strip()
                    local_log(f"✅ Ответ получен: {resp_text[:50]}...")
                else:
                    local_log("⚠️ Сервер не прислал ответа, но данные отправлены.")
                    resp_text = "Sent (no response)"

            # Разблокируем кнопку ПЕРЕД вызовом успеха
            QTimer.singleShot(0, lambda: btn.setEnabled(True))
            QTimer.singleShot(0, lambda: self._on_send_success(resp_text, btn, is_direct=True))
            
        except socket.timeout:
            local_log("❌ Ошибка: Таймаут соединения/чтения.")
            QTimer.singleShot(0, lambda: btn.setEnabled(True))
            QTimer.singleShot(0, lambda: self._on_send_error("Таймаут (сервер молчит)", btn))
        except ConnectionRefusedError:
            local_log(f"❌ Ошибка: Сервер {ip}:{port} отклонил подключение.")
            QTimer.singleShot(0, lambda: btn.setEnabled(True))
            QTimer.singleShot(0, lambda: self._on_send_error(f"Сервер {ip}:{port} недоступен", btn))
        except Exception as e:
            local_log(f"❌ Критическая ошибка: {type(e).__name__}: {e}")
            QTimer.singleShot(0, lambda: btn.setEnabled(True))
            QTimer.singleShot(0, lambda: self._on_send_error(str(e), btn))

    def _ai_send_worker(self, ip, port, message, btn):
        """Реальная отправка через Ollama с полной отладкой и защитой - УЛУЧШЕННАЯ ВЕРСИЯ"""
        import requests
        import json
        import traceback

        def unlock_button():
            """Безопасная разблокировка кнопки"""
            try:
                if btn is not None:
                    btn.setEnabled(True)
            except (RuntimeError, AttributeError):
                pass  # Кнопка могла быть уничтожена
        
        try:
            print("[DEBUG AI] Запуск worker...")
            self._update_node("node_ai", "active", "Инициализация модели...")
            self._log("[AI] Формирование запроса к Ollama...")

            prompt = (
                f"You are a signal classifier. Input: '{message}'. "
                f"Task: Return ONLY a valid JSON object with NO markdown, NO explanations, NO extra text. "
                f"Required format: {{\"classification\":\"NORMAL\",\"priority\":1,\"response\":\"PROCESSED: {message}\"}}. "
                f"Rules: 1) classification must be NORMAL or EMERGENCY. 2) priority is integer 1-5. 3) response is short confirmation. "
                f"Output ONLY the JSON string starting with {{ and ending with }}."
            )
            
            payload = {
                "model": self.config.get("ai", "default_model", default="phi3:mini"),
                "prompt": prompt,
                "stream": False,          # ← КРИТИЧНО: иначе json() зависнет
                "options": {
                    "temperature": 0.0,
                    "num_predict": 120,
                    "repeat_penalty": 1.1
                }
            }

            ollama_url = self.config.get("ai", "ollama_url", default="http://localhost:11434/api/generate")
            print(f"[DEBUG AI] Отправка POST на {ollama_url}")
            
            # 60 сек на первый запуск (модель грузится в RAM/VRAM)
            response = requests.post(ollama_url, json=payload, timeout=60)
            response.raise_for_status()
            
            raw = response.json().get("response", "")
            print(f"[DEBUG AI] Ответ получен. Длина: {len(raw)} символов")
            self._log("[AI] Ответ получен. Очистка от markdown...")

            # Убираем ```json ... ``` если ИИ его добавил
            if "```" in raw:
                raw = raw.split("```")[-2] if raw.count("```") >= 2 else raw.replace("```", "")
            
            # Удаляем префиксы типа "json", "markdown" в начале строки (после очистки от ```)
            raw = raw.strip()
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()
            elif raw.lower().startswith("markdown"):
                raw = raw[8:].strip()
            raw = raw.strip()

            # DEBUG: Вывод сырого ответа для анализа проблемы
            self._log(f"[DEBUG] RAW AI RESPONSE: {repr(raw)}")

            try:
                analysis = json.loads(raw)
                self._log(f"[AI] JSON успешно распарсен: {analysis}")
                processed_msg = analysis.get("response", f"AI_OK: {message}")
            except json.JSONDecodeError as je:
                print(f"[DEBUG AI] JSON парсинг упал: {je}")
                self._log(f"[AI WARN] JSON не распарсен: {je}")
                self._log(f"[AI WARN] Содержимое: {raw[:200]}...")
                processed_msg = f"AI_FALLBACK: {message}"
                self._log("[AI WARN] Использован fallback режим")

            self._log(f"[AI] Отправка на сервер: {processed_msg[:40]}...")
            
            # === ОТПРАВКА НА СЕРВЕР - УЛУЧШЕННАЯ ВЕРСИЯ ===
            server_response = "Sent (no response)"
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(10.0)
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                    
                    self._log(f"[AI] Подключение к {ip}:{port}...")
                    s.connect((ip, port))
                    self._log(f"[AI] ✅ Соединение установлено")
                    
                    data_to_send = (processed_msg + "\n").encode('utf-8')
                    self._log(f"[AI] Отправка {len(data_to_send)} байт...")
                    s.sendall(data_to_send)
                    self._log(f"[AI] ✅ Данные отправлены")
                    
                    # Читаем ответ порциями
                    resp_data = b""
                    s.settimeout(5.0)
                    while True:
                        try:
                            chunk = s.recv(4096)
                            if not chunk:
                                break
                            resp_data += chunk
                            if len(chunk) < 4096:
                                break
                        except socket.timeout:
                            break

                server_response = resp_data.decode('utf-8', errors='replace').strip() if resp_data else "Sent (no response)"
                print(f"[DEBUG AI] Успех. Ответ сервера: {server_response}")
            except Exception as sock_err:
                self._log(f"[AI ERROR] Ошибка соединения с сервером: {sock_err}")
                raise  # Пробрасываем исключение дальше для обработки
            
            # Разблокируем кнопку ПЕРЕД вызовом успеха
            unlock_button()
            QTimer.singleShot(0, lambda: self._on_send_success(server_response, btn, is_direct=False))

        except requests.exceptions.ConnectionError as ce:
            print(f"[DEBUG AI] ConnectionError: {ce}")
            unlock_button()
            QTimer.singleShot(0, lambda: self._on_send_error("Ollama API недоступен. Запущен ли ollama serve?", btn))
        except requests.exceptions.Timeout as te:
            print(f"[DEBUG AI] Timeout: {te}")
            unlock_button()
            QTimer.singleShot(0, lambda: self._on_send_error("Таймаут Ollama (60с). Модель слишком долго грузится в RAM.", btn))
        except Exception as e:
            print(f"[DEBUG AI] Неизвестная ошибка:\n{traceback.format_exc()}")
            unlock_button()
            QTimer.singleShot(0, lambda: self._on_send_error(f"AI-поток: {e}", btn))

    def _on_send_success(self, response, btn, is_direct: bool):
        mode = "DIRECT" if is_direct else "AI"
        self._log(f"[✅ {mode}] Ответ: {response}")
        self._update_node("node_sender", "success", "Доставлено")
        self._update_node("node_receiver", "success", "Принято")
        self.delivery_status.setText(f"✅ Доставка успешна ({mode})")
        self.delivery_status.setProperty("class", "status-ok")
        self._refresh_style(self.delivery_status)
        # Кнопка уже разблокирована в worker'е, здесь не трогаем
        QTimer.singleShot(3000, self._reset_nodes)

    def _on_send_error(self, error, btn):
        self._log(f"[❌ ERROR] {error}")
        self._update_node("node_sender", "error", "Ошибка")
        self._update_node("node_receiver", "error", "Сбой")
        self.delivery_status.setText("❌ Ошибка соединения")
        self.delivery_status.setProperty("class", "status-error")
        self._refresh_style(self.delivery_status)
        # Кнопка уже разблокирована в worker'е, здесь не трогаем
        QTimer.singleShot(3000, self._reset_nodes)

    def _reset_nodes(self):
        self._update_node("node_sender", "idle", "Готов")
        self._update_node("node_ai", "idle", "Ожидание")
        self._update_node("node_receiver", "idle", "Готов")
        self.delivery_status.setText("📡 Готов к работе")
        self.delivery_status.setProperty("class", "")
        self._refresh_style(self.delivery_status)

    def _update_node(self, node_name: str, state: str, text: str):
        node = getattr(self, node_name, None)
        if node:
            node.setProperty("class", f"node {state}")
            node.lbl_status.setText(text)
            self._refresh_style(node)

    def _refresh_style(self, widget):
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _get_pc_status(self) -> str:
        """Получение статуса ПК с расширенной информацией"""
        import psutil
        
        try:
            cpu_percent = psutil.cpu_percent(interval=0.5)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return (f"PC_STATUS: OS={platform.system()} {platform.release()}; "
                    f"HOST={platform.node()}; PY={platform.python_version()}; "
                    f"CPU={cpu_percent}%; RAM={memory.percent}%; DISK={disk.percent}%")
        except ImportError:
            # Если psutil не установлен, возвращаем базовую информацию
            return (f"PC_STATUS: OS={platform.system()} {platform.release()}; "
                    f"HOST={platform.node()}; PY={platform.python_version()}")
        except Exception as e:
            return f"PC_STATUS: ERROR={str(e)}"

    def _emergency_stop(self):
        self.process_mgr.stop("simulator", force=True)
        self.process_mgr.stop("processor", force=True)
        self._log("[🔴 SYSTEM] EMERGENCY STOP")
        self._update_node("node_sender", "error", "СТОП")
        self._update_node("node_ai", "error", "СТОП")
        self._update_node("node_receiver", "error", "СТОП")
        self.delivery_status.setText("🔴 Процессы прерваны")
        self.send_btn.setEnabled(True)
        self.direct_send_btn.setEnabled(True)
        self.pc_status_btn.setEnabled(True)

    def _log(self, message: str):
        # Метод лога теперь можно вызывать через QTimer.singleShot(0, lambda: self._log(...)) из потока
        self.log_text.appendPlainText(message)
        vscroll = self.log_text.verticalScrollBar()
        vscroll.setValue(vscroll.maximum())

    def _on_lang_change(self, lang: str):
        self.tr.set_language(lang.lower())
        self.retranslate()

    def retranslate(self):
        self.setWindowTitle(self.tr.t("app_title", default="T-Invest News Hub"))
        self.send_btn.setText(self.tr.t("btn_send_msg", default="📤 Отправить сообщение"))
        self.direct_send_btn.setText(self.tr.t("btn_direct_send", default="⚡ Прямая отправка (без ИИ)"))
        self.pc_status_btn.setText(self.tr.t("btn_send_pc", default="💻 Отправить статус ПК"))
        self.emergency_btn.setText(self.tr.t("btn_emergency", default="🔴 ЭКСТРЕННАЯ ОСТАНОВКА"))
        self.model_label.setText(self.tr.t("model_active", model=self.config.get("ai", "default_model", default="phi3:mini")))
        self._reset_nodes()