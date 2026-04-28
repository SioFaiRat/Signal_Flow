import sys
import io
import socket
import threading
import platform
import json
import requests
from pathlib import Path
    

if sys.platform == "win32": # Принудительно устанавливаем UTF-8 для консоли Windows
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QPushButton, QLabel, QComboBox, QPlainTextEdit, QFrame)
from PyQt6.QtCore import Qt, QTimer
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

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.config = AppConfig()
        self.tr = Translator(self.config.get("ui", "default_language", default="ru"))
        self.process_mgr = ProcessManager()
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

    def _trigger_send(self, message: str, btn: QPushButton, use_ai: bool):
        if not message:
            self._log("[!] Нет данных для отправки")
            return

        btn.setEnabled(False)
        ip = self.config.get("network", "simulator_host", default="127.0.0.1")
        port = int(self.config.get("network", "simulator_port", default=9999))

        if use_ai:
            self._log(f"[AI] Подготовка через ИИ-модуль...")
            self._update_node("node_sender", "active", "В очереди ИИ...")
            threading.Thread(target=self._ai_send_worker, args=(ip, port, message, btn), daemon=True).start()
        else:
            self._log(f"[DIRECT] Прямая отправка на {ip}:{port}...")
            self._update_node("node_sender", "active", "Отправка...")
            threading.Thread(target=self._direct_send_worker, args=(ip, port, message, btn), daemon=True).start()

    def _direct_send_worker(self, ip, port, message, btn):
        def local_log(msg): QTimer.singleShot(0, lambda: self._log(f"[DEBUG] {msg}"))
        
        try:
            local_log(f"Начало потока. Цель: {ip}:{port}")
            QTimer.singleShot(0, lambda: self._update_node("node_receiver", "active", "Соединение..."))
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5.0) # Увеличим таймаут для теста
                
                local_log("Попытка установить TCP-соединение...")
                s.connect((ip, port))
                local_log("Соединение установлено успешно.")
                
                local_log("Отправка данных...")
                s.sendall((message + "\n").encode('utf-8'))
                local_log("Данные ушли в сокет.")
                
                local_log("Ожидание ответа от сервера (recv)...")
                # Читаем только один блок, чтобы не висеть в цикле
                response = s.recv(4096) 
                
                if not response:
                    local_log("Сервер закрыл соединение, не прислав данных.")
                    resp_text = "Empty Response"
                else:
                    resp_text = response.decode('utf-8', errors='replace').strip()
                    local_log(f"Ответ получен: {resp_text[:30]}...")

            QTimer.singleShot(0, lambda: self._on_send_success(resp_text, btn, is_direct=True))
            
        except socket.timeout:
            local_log("Ошибка: Таймаут соединения/чтения.")
            QTimer.singleShot(0, lambda: self._on_send_error("Таймаут (сервер молчит)", btn))
        except Exception as e:
            local_log(f"Критическая ошибка: {type(e).__name__}: {e}")
            QTimer.singleShot(0, lambda: self._on_send_error(str(e), btn))

    def _ai_send_worker(self, ip, port, message, btn):
        """Реальная отправка через Ollama с полной отладкой и защитой"""
        import requests
        import json
        import traceback

        try:
            print("[DEBUG AI] Запуск worker...")
            self._update_node("node_ai", "active", "Инициализация модели...")
            self._log("[AI] Формирование запроса к Ollama...")

            prompt = (
                f"Classify signal: {message}. "
                f"Output ONLY valid JSON: "
                f'{{"classification":"NORMAL|EMERGENCY","priority":5,"response":"OK: processed"}}'
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
            raw = raw.strip()

            try:
                analysis = json.loads(raw)
                processed_msg = analysis.get("response", f"AI_OK: {message}")
            except json.JSONDecodeError as je:
                print(f"[DEBUG AI] JSON парсинг упал: {je}")
                processed_msg = f"AI_FALLBACK: {message}"
                self._log("[AI WARN] JSON не распарсен, использован fallback")

            self._log(f"[AI] Отправка на сервер: {processed_msg[:40]}...")
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                s.connect((ip, port))
                s.sendall(processed_msg.encode('utf-8'))
                
                resp_data = b""
                while True:
                    try:
                        chunk = s.recv(1024)
                        if not chunk: break
                        resp_data += chunk
                    except socket.timeout: break

            final_resp = resp_data.decode('utf-8', errors='replace').strip()
            print(f"[DEBUG AI] Успех. Ответ сервера: {final_resp}")
            QTimer.singleShot(0, lambda: self._on_send_success(final_resp, btn, is_direct=False))

        except requests.exceptions.ConnectionError as ce:
            print(f"[DEBUG AI] ConnectionError: {ce}")
            QTimer.singleShot(0, lambda: self._on_send_error("Ollama API недоступен. Запущен ли ollama serve?", btn))
        except requests.exceptions.Timeout as te:
            print(f"[DEBUG AI] Timeout: {te}")
            QTimer.singleShot(0, lambda: self._on_send_error("Таймаут Ollama (60с). Модель слишком долго грузится в RAM.", btn))
        except Exception as e:
            print(f"[DEBUG AI] Неизвестная ошибка:\n{traceback.format_exc()}")
            QTimer.singleShot(0, lambda: self._on_send_error(f"AI-поток: {e}", btn))
        finally:
            # Гарантированно разблокируем кнопку и сбрасываем статус, если что-то пошло не так
            QTimer.singleShot(0, lambda: btn.setEnabled(True))

    def _on_send_success(self, response, btn, is_direct: bool):
        mode = "DIRECT" if is_direct else "AI"
        self._log(f"[✅ {mode}] Ответ: {response}")
        self._update_node("node_sender", "success", "Доставлено")
        self._update_node("node_receiver", "success", "Принято")
        self.delivery_status.setText(f"✅ Доставка успешна ({mode})")
        self.delivery_status.setProperty("class", "status-ok")
        self._refresh_style(self.delivery_status)
        btn.setEnabled(True)
        QTimer.singleShot(3000, self._reset_nodes)

    def _on_send_error(self, error, btn):
        self._log(f"[❌ ERROR] {error}")
        self._update_node("node_sender", "error", "Ошибка")
        self._update_node("node_receiver", "error", "Сбой")
        self.delivery_status.setText("❌ Ошибка соединения")
        self.delivery_status.setProperty("class", "status-error")
        self._refresh_style(self.delivery_status)
        btn.setEnabled(True)
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
        return (f"PC_STATUS: OS={platform.system()} {platform.release()}; "
                f"HOST={platform.node()}; PY={platform.python_version()}")

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