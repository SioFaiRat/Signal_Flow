import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from PyQt6.QtWidgets import QApplication
from src.gui.main_window import MainWindow


def load_stylesheet() -> str:
    style_path = Path("src/gui/styles.qss")
    if style_path.exists():
        return style_path.read_text(encoding="utf-8")
    return ""

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(load_stylesheet())
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()