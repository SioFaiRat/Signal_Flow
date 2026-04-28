"""
SignalFlow Controller - Main Entry Point

A PyQt6-based GUI application for managing signal processing pipeline
with Ollama AI integration and TCP communication.
"""
import sys
from pathlib import Path

# Add project root to Python path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from src.gui.main_window import MainWindow


def load_stylesheet() -> str:
    """Load application stylesheet from QSS file."""
    style_path = ROOT_DIR / "src" / "gui" / "styles.qss"
    if style_path.exists():
        return style_path.read_text(encoding="utf-8")
    return ""


def setup_application() -> QApplication:
    """Configure and return QApplication instance."""
    app = QApplication(sys.argv)
    app.setApplicationName("SignalFlow Controller")
    app.setOrganizationName("SignalFlow")
    app.setStyle("Fusion")
    app.setStyleSheet(load_stylesheet())
    return app


def main() -> int:
    """Main application entry point."""
    app = setup_application()
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())