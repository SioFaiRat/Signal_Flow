"""
SignalFlow Controller - GUI Widgets

Custom PyQt6 widgets for the application.
"""
from PyQt6.QtWidgets import QLabel, QProgressBar
from PyQt6.QtCore import QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve


class TypingLabel(QLabel):
    """Label that displays text with a typing animation effect."""

    typing_finished = pyqtSignal(str)

    def __init__(self, parent: "QWidget | None" = None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._type_next_char)
        self._text = ""
        self._index = 0
        self._interval = 30

    def type_text(self, text: str, interval: int = 30) -> None:
        """
        Start typing animation for the given text.

        Args:
            text: Text to display.
            interval: Delay between characters in milliseconds.
        """
        self._text = text
        self._index = 0
        self._interval = interval
        self.setText("")
        self._timer.start(interval)

    def _type_next_char(self) -> None:
        """Animate next character."""
        if self._index < len(self._text):
            self.setText(self._text[:self._index + 1])
            self._index += 1
        else:
            self._timer.stop()
            self.typing_finished.emit(self._text)

    def stop(self) -> None:
        """Stop animation and show full text."""
        self._timer.stop()
        self.setText(self._text)


class AnimatedProgressBar(QProgressBar):
    """Progress bar with smooth animation for value changes."""

    def __init__(self, parent: "QWidget | None" = None):
        super().__init__(parent)
        self.setValue(0)
        self._animation = QPropertyAnimation(self, b"value")
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.setDuration(600)

    def animate_to(self, value: int) -> None:
        """
        Animate progress to specified value.

        Args:
            value: Target value (0-100).
        """
        if self._animation.state() == QPropertyAnimation.State.Running:
            self._animation.stop()
        self._animation.setEndValue(value)
        self._animation.start()

    def reset(self) -> None:
        """Reset progress to zero with animation."""
        self.animate_to(0)