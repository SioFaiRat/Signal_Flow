"""
SignalFlow Controller - AI Processor

Simulates AI processing of messages with configurable delays.
"""
import random
import time
from datetime import datetime
from typing import List


class AIProcessor:
    """AI message processor with simulated analysis capabilities."""

    DEFAULT_MESSAGES: List[str] = [
        "STATUS: ONLINE; BATTERY=87%",
        "EMERGENCY: GEO=55.7522,37.6156; BATTERY=3%",
        "PING: LATENCY=42ms",
        "HEALTH: STEPS=8421; HR=72bpm"
    ]

    def __init__(self, messages: List[str] | None = None):
        """
        Initialize AI processor.

        Args:
            messages: Optional list of messages to process.
        """
        self.messages = messages or self.DEFAULT_MESSAGES.copy()
        self._running = False

    def process_message(self, message: str) -> dict:
        """
        Process a single message (simulated).

        Args:
            message: Input message to process.

        Returns:
            Dictionary with processing results.
        """
        return {
            "original": message,
            "processed": f"PROCESSED: {message}",
            "timestamp": datetime.now().isoformat(),
            "classification": "NORMAL" if "EMERGENCY" not in message else "EMERGENCY"
        }

    def run_simulation(self, count: int = 10, delay: float = 2.0) -> List[dict]:
        """
        Run batch processing simulation.

        Args:
            count: Number of messages to process.
            delay: Delay between processing each message.

        Returns:
            List of processing results.
        """
        self._running = True
        results = []

        for i in range(count):
            if not self._running:
                break
            msg = random.choice(self.messages)
            result = self.process_message(msg)
            results.append(result)
            time.sleep(delay)

        self._running = False
        return results

    def stop(self) -> None:
        """Stop the running simulation."""
        self._running = False

    @property
    def is_running(self) -> bool:
        """Check if processor is currently running."""
        return self._running


def main():
    """CLI entry point for testing."""
    print("[+] AI Processor started. Waiting for signals...")
    processor = AIProcessor()
    processor.run_simulation()
    print("[+] AI Processor finished.")


if __name__ == "__main__":
    main()