import subprocess
import threading
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal

class ProcessManager(QObject):
    process_started = pyqtSignal(str)  # name
    process_stopped = pyqtSignal(str)  # name
    log_line = pyqtSignal(str, str)    # source, message
    error_occurred = pyqtSignal(str, str)  # source, error
    delivery_status = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.processes: dict[str, subprocess.Popen] = {}
        self._threads: dict[str, threading.Thread] = {}

    def start(self, name: str, script: str, cwd: str = "."):
        if name in self.processes and self.processes[name].poll() is None:
            self.log_line.emit("SYSTEM", f"[WARN] {name} уже запущен")
            return False

        cmd = ["python", Path(script).resolve()]
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=cwd,
                creationflags=subprocess.CREATE_NO_WINDOW  # Windows: без консоли
            )
            self.processes[name] = proc
            self._threads[name] = threading.Thread(
                target=self._read_output, args=(name, proc), daemon=True
            )
            self._threads[name].start()
            self.process_started.emit(name)
            self.log_line.emit("SYSTEM", f"[OK] {name} запущен")
            return True
        except Exception as e:
            self.error_occurred.emit(name, str(e))
            return False

    def stop(self, name: str, force: bool = False):
        proc = self.processes.get(name)
        if not proc or proc.poll() is not None:
            return False

        try:
            if force:
                proc.kill()
            else:
                proc.terminate()
                proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        except Exception as e:
            self.error_occurred.emit(name, str(e))
            return False

        self.process_stopped.emit(name)
        self.log_line.emit("SYSTEM", f"[STOP] {name} остановлен")
        del self.processes[name]
        return True

    def _read_output(self, name: str, proc: subprocess.Popen):
        for line in iter(proc.stdout.readline, ""):
            if line:
                self.log_line.emit(name, line.strip())
                if "OK:" in line:
                    self.delivery_status.emit("success", "Cообщение доставлено")
                elif "ERROR" in line or "Error" in line:
                    self.delivery_status.emit("error", "Ошибка доставки")
        proc.stdout.close()