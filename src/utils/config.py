"""
SignalFlow Controller - Configuration Manager

Handles loading and accessing application configuration from JSON file.
"""
import json
from pathlib import Path
from typing import Any


class AppConfig:
    """Application configuration manager with nested key access support."""

    def __init__(self, config_path: str = "config.json"):
        """
        Initialize configuration manager.

        Args:
            config_path: Relative path to config file from project root.
        """
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.path = self.project_root / config_path
        self.data = self._load()

    def _load(self) -> dict[str, Any]:
        """Load configuration from JSON file."""
        if not self.path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {self.path}\n"
                f"Please create config.json in the project root directory."
            )
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get(self, *keys: str, default: Any = None) -> Any:
        """
        Safely access nested configuration keys.

        Args:
            *keys: Variable number of keys for nested access.
            default: Default value if key path doesn't exist.

        Returns:
            Configuration value or default.

        Example:
            config.get("network", "port", default=9999)
        """
        data: Any = self.data
        for key in keys:
            if isinstance(data, dict) and key in data:
                data = data[key]
            else:
                return default
        return data

    def reload(self) -> None:
        """Reload configuration from file."""
        self.data = self._load()