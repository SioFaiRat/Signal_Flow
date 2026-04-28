import socket
import threading
import sys
from datetime import datetime

def handle_client(conn, addr):
    with conn:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Connected: {addr[0]}:{addr[1]}")
        try:
            while True:
                data = conn.recv(1024)
                if not data: break
                signal = data.decode('utf-8', errors='replace').strip()
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Received: {signal}")
                conn.send(f"OK: {signal[:30]}".encode('utf-8'))
        except Exception as e:
            print(f"[!] Error: {e}")

def main():
    host, port = "127.0.0.1", 9999
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen(5)
        print(f"[+] Server started on {host}:{port}")
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)