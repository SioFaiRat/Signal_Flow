from PyQt6.QtWidgets import QLabel, QProgressBar
from PyQt6.QtCore import QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve

class TypingLabel(QLabel):
    typing_finished = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._type_next_char)
        self._text = ""
        self._index = 0
        self._interval = 30

    def type_text(self, text: str, interval: int = 30):
        self._text = text
        self._index = 0
        self._interval = interval
        self.setText("")
        self.timer.start(interval)

    def _type_next_char(self):
        if self._index < len(self._text):
            self.setText(self._text[:self._index + 1])
            self._index += 1
        else:
            self.timer.stop()
            self.typing_finished.emit(self._text)

    def stop(self):
        self.timer.stop()
        self.setText(self._text)

class AnimatedProgressBar(QProgressBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setValue(0)
        self.anim = QPropertyAnimation(self, b"value")
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.setDuration(600)

    def animate_to(self, value: int):
        if self.anim.state() == QPropertyAnimation.State.Running:
            self.anim.stop()
        self.anim.setEndValue(value)
        self.anim.start()

    def reset(self):
        self.animate_to(0)