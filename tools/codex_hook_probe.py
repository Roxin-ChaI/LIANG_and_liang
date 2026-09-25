"""Fail-open, metadata-only Codex lifecycle hook.

The hook intentionally discards prompt, tool input/output, transcript paths and
other fields from Codex's stdin payload. A missing listener is not an error.
"""

from __future__ import annotations

import datetime as dt
import json
import socket
import sys


EVENTS = frozenset({
    "SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse",
    "PermissionRequest", "Stop", "SessionEnd",
})
MAX_INPUT_BYTES = 1_048_576


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
            deliver(event, args[0])
    except (OSError, UnicodeError, ValueError, TypeError):
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
