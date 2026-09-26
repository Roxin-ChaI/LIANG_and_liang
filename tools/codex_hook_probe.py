"""Fail-open, metadata-only Codex lifecycle hook.

The hook intentionally discards prompt, tool input/output, transcript paths and
other fields from Codex's stdin payload. A missing listener is not an error.
"""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import socket
import stat
import sys


EVENTS = frozenset({
    "SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse",
    "PermissionRequest", "Stop", "SessionEnd",
})
MAX_INPUT_BYTES = 1_048_576
DIAGNOSTIC_PATH = Path(
    "/Users/mac/Projects/liang-no-henshin/.cache/hook-entry-diagnostic.jsonl"
)


def metadata(payload: object, now: dt.datetime | None = None) -> dict[str, str] | None:
    if not isinstance(payload, dict):
        return None
    event = payload.get("hook_event_name")
    session = payload.get("session_id")
    if event not in EVENTS or not isinstance(session, str) or not (0 < len(session) <= 256):
        return None
    instant = now or dt.datetime.now(dt.timezone.utc)
    return {
        "event": event,
        "session_id": session,
        "timestamp": instant.astimezone(dt.timezone.utc).isoformat(timespec="milliseconds"),
    }


def deliver(event: dict[str, str], socket_path: str) -> None:
    wire = (json.dumps(event, separators=(",", ":")) + "\n").encode("utf-8")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(0.05)
        client.connect(socket_path)
        client.sendall(wire)


def write_diagnostic(event: dict[str, str], path: Path = DIAGNOSTIC_PATH,
                     pid: int | None = None) -> None:
    """Append only permitted metadata to a private, non-symlink local file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        details = os.fstat(descriptor)
        if not stat.S_ISREG(details.st_mode) or details.st_uid != os.getuid():
            return
        os.fchmod(descriptor, 0o600)
        record = {"event": event["event"], "timestamp": event["timestamp"],
                  "pid": os.getpid() if pid is None else pid,
                  "session_id": event["session_id"]}
        os.write(descriptor, (json.dumps(record, separators=(",", ":")) + "\n").encode())
    finally:
        os.close(descriptor)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        return 0
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            return 0
        event = metadata(json.loads(raw))
        if event is not None:
            try:
                write_diagnostic(event)
            except OSError:
                pass
            try:
                deliver(event, args[0])
            except OSError:
                pass
    except (OSError, UnicodeError, ValueError, TypeError):
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
