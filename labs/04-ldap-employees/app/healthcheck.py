"""Sonda de salud del gateway: manda HEALTH por TCP y espera la linea HEALTH."""

import socket
import sys

HOST = "127.0.0.1"
PORT = 1389


def main():
    """Devuelve 0 si el gateway contesta HEALTH, 1 en cualquier otro caso."""
    with socket.create_connection((HOST, PORT), timeout=5) as sock:
        sock.settimeout(5)
        sock.sendall(b"HEALTH\n")
        buffer = b""
        while b"HEALTH\n" not in buffer:
            chunk = sock.recv(4096)
            if not chunk:
                return 1
            buffer += chunk
    return 0


if __name__ == "__main__":
    sys.exit(main())
