"""Local, project-scoped collector of already-minimized hook metadata."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import socket

from codex_hook_probe import EVENTS


def accept_metadata(value: object) -> dict[str, str] | None:
    if not isinstance(value, dict) or set(value) != {"event", "session_id", "timestamp"}:
        return None
    if value["event"] not in EVENTS:
        return None
    if not all(isinstance(value[key], str) and 0 < len(value[key]) <= 256 for key in value):
        return None
    return value


def forward_metadata(value: dict[str, str], forward_path: Path | None) -> bool:
    """Best-effort delivery to the standalone pet; logging stays independent."""
    if forward_path is None:
        return False
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(0.05)
            client.connect(str(forward_path))
            client.sendall((json.dumps(value, separators=(",", ":")) + "\n").encode("utf-8"))
        return True
    except OSError:
        return False


def serve(socket_path: Path, log_path: Path, forward_path: Path | None = None) -> None:
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if socket_path.exists():
        raise FileExistsError(f"socket already exists: {socket_path}")
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listener.bind(str(socket_path))
    os.chmod(socket_path, 0o600)
    listener.listen(16)
    listener.settimeout(0.5)
    running = True

    def stop(_signum: int, _frame: object) -> None:
        nonlocal running
        running = False

    previous_int = signal.signal(signal.SIGINT, stop)
    previous_term = signal.signal(signal.SIGTERM, stop)
    try:
        while running:
            try:
                connection, _ = listener.accept()
            except socket.timeout:
                continue
            with connection:
                connection.settimeout(0.1)
                try:
                    raw = connection.recv(4096)
                    value = accept_metadata(json.loads(raw))
                except (OSError, UnicodeError, ValueError, TypeError):
                    value = None
                if value is not None:
                    with log_path.open("a", encoding="utf-8") as log:
                        log.write(json.dumps(value, separators=(",", ":")) + "\n")
                    forward_metadata(value, forward_path)
    finally:
        listener.close()
        socket_path.unlink(missing_ok=True)
        signal.signal(signal.SIGINT, previous_int)
        signal.signal(signal.SIGTERM, previous_term)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--socket", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--forward-socket", type=Path)
    arguments = parser.parse_args()
    serve(arguments.socket, arguments.log, arguments.forward_socket)
