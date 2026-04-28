"""
SignalFlow Controller - Logging Utility

Provides structured logging functionality for the application.
"""
import logging
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str = "signalflow",
    level: int = logging.INFO,
    log_dir: Optional[str] = None
) -> logging.Logger:
    """
    Configure and return a logger instance.

    Args:
        name: Logger name.
        level: Logging level.
        log_dir: Directory for log files (optional).

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)

        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S"
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        if log_dir:
            log_path = Path(log_dir)
            log_path.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_path / f"{name}.log")
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "signalflow") -> logging.Logger:
    """
    Get existing logger or create new one.

    Args:
        name: Logger name.

    Returns:
        Logger instance.
    """
    return logging.getLogger(name)