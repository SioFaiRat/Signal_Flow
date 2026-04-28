"""
SignalFlow Controller - TCP Server

Simple TCP server for receiving signals from clients.
"""
import socket
import threading
import sys
from datetime import datetime
from typing import Callable, Optional


class TCPServer:
    """TCP server for handling client connections."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 9999,
        on_message: Optional[Callable[[str, tuple], str]] = None
    ):
        """
        Initialize TCP server.

        Args:
            host: Server bind address.
            port: Server bind port.
            on_message: Optional callback for processing received messages.
        """
        self.host = host
        self.port = port
        self.on_message = on_message or self._default_handler
        self._socket: Optional[socket.socket] = None
        self._running = False
        self._accept_thread: Optional[threading.Thread] = None

    def _default_handler(self, message: str, addr: tuple) -> str:
        """Default message handler."""
        return f"OK: {message[:30]}"

    def start(self) -> bool:
        """
        Start the TCP server.

        Returns:
            True if started successfully.
        """
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.bind((self.host, self.port))
            self._socket.listen(5)
            self._running = True

            self._accept_thread = threading.Thread(
                target=self._accept_connections, daemon=True
            )
            self._accept_thread.start()

            print(f"[+] Server started on {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"[!] Server start error: {e}")
            return False

    def _accept_connections(self) -> None:
        """Accept and handle client connections."""
        while self._running and self._socket:
            try:
                conn, addr = self._socket.accept()
                thread = threading.Thread(
                    target=self._handle_client, args=(conn, addr), daemon=True
                )
                thread.start()
            except OSError:
                break

    def _handle_client(self, conn: socket.socket, addr: tuple) -> None:
        """Handle a single client connection."""
        with conn:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Connected: {addr[0]}:{addr[1]}")
            try:
                while self._running:
                    data = conn.recv(1024)
                    if not data:
                        break
                    message = data.decode('utf-8', errors='replace').strip()
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Received: {message}")

                    response = self.on_message(message, addr)
                    conn.send(response.encode('utf-8'))
            except Exception as e:
                print(f"[!] Client error: {e}")

    def stop(self) -> None:
        """Stop the TCP server."""
        self._running = False
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None

    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._running


def main():
    """CLI entry point for running standalone server."""
    server = TCPServer()
    try:
        server.start()
        while True:
            threading.Event().wait(1)
    except KeyboardInterrupt:
        print("\n[+] Shutting down server...")
        server.stop()
        sys.exit(0)


if __name__ == "__main__":
    main()