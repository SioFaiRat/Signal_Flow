"""
SignalFlow Controller - Process Manager

Manages subprocess execution for core components with thread-safe logging.
"""
import subprocess
import threading
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal


class ProcessManager(QObject):
    """Manages multiple subprocesses with signal-based communication."""

    process_started = pyqtSignal(str)  # name
    process_stopped = pyqtSignal(str)  # name
    log_line = pyqtSignal(str, str)    # source, message
    error_occurred = pyqtSignal(str, str)  # source, error
    delivery_status = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self._processes: dict[str, subprocess.Popen] = {}
        self._threads: dict[str, threading.Thread] = {}
        self._lock = threading.Lock()

    def start(self, name: str, script: str, cwd: str = ".") -> bool:
        """
        Start a subprocess.

        Args:
            name: Process identifier.
            script: Python script path to execute.
            cwd: Working directory.

        Returns:
            True if started successfully, False otherwise.
        """
        with self._lock:
            if name in self._processes and self._processes[name].poll() is None:
                self.log_line.emit("SYSTEM", f"[WARN] {name} already running")
                return False

        cmd = ["python", Path(script).resolve()]
        try:
            creationflags = 0
            if hasattr(subprocess, "CREATE_NO_WINDOW"):
                creationflags = subprocess.CREATE_NO_WINDOW

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=cwd,
                creationflags=creationflags
            )
            
            with self._lock:
                self._processes[name] = proc
            
            thread = threading.Thread(
                target=self._read_output, args=(name, proc), daemon=True
            )
            with self._lock:
                self._threads[name] = thread
            thread.start()
            
            self.process_started.emit(name)
            self.log_line.emit("SYSTEM", f"[OK] {name} started")
            return True
        except Exception as e:
            self.error_occurred.emit(name, str(e))
            return False

    def stop(self, name: str, force: bool = False) -> bool:
        """
        Stop a subprocess.

        Args:
            name: Process identifier.
            force: If True, kill the process immediately.

        Returns:
            True if stopped successfully, False otherwise.
        """
        with self._lock:
            proc = self._processes.get(name)
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
        self.log_line.emit("SYSTEM", f"[STOP] {name} stopped")
        
        with self._lock:
            del self._processes[name]
        return True

    def _read_output(self, name: str, proc: subprocess.Popen) -> None:
        """Read and emit process output in a background thread."""
        try:
            for line in iter(proc.stdout.readline, ""):
                if line:
                    self.log_line.emit(name, line.strip())
                    if "OK:" in line:
                        self.delivery_status.emit("success", "Message delivered")
                    elif "ERROR" in line or "Error" in line:
                        self.delivery_status.emit("error", "Delivery failed")
        finally:
            proc.stdout.close()

    def is_running(self, name: str) -> bool:
        """Check if a process is currently running."""
        with self._lock:
            proc = self._processes.get(name)
            return proc is not None and proc.poll() is None

    def stop_all(self, force: bool = False) -> None:
        """Stop all managed processes."""
        with self._lock:
            names = list(self._processes.keys())
        for name in names:
            self.stop(name, force)