"""Strict development client for the Liang local Pet bridge protocol v1."""

from __future__ import annotations

import argparse
import json
import os
import socket
import tempfile
import uuid
from pathlib import Path
from typing import Any


PROTOCOL_VERSION = 1
MAX_MESSAGE_BYTES = 4096
MAX_REQUEST_ID_LENGTH = 128


class PetRuntimeClientError(RuntimeError):
    """Safe client error with a stable machine-readable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def default_socket_path() -> Path:
    path = Path(tempfile.gettempdir()) / f"liang-no-henshin-{os.getuid()}" / "runtime.sock"
    if len(os.fsencode(path)) > 100:
        raise PetRuntimeClientError("SOCKET_PATH_TOO_LONG", "Unix socket path exceeds the macOS limit")
    return path


def _valid_request_id(value: object) -> bool:
    return (
        isinstance(value, str)
        and 0 < len(value) <= MAX_REQUEST_ID_LENGTH
        and all(character.isascii() and (character.isalnum() or character in "._:-") for character in value)
    )


def _parse_response(raw: bytes, request_id: str) -> dict[str, Any]:
    if not raw.endswith(b"\n") or raw.count(b"\n") != 1 or len(raw) > MAX_MESSAGE_BYTES + 1:
        raise PetRuntimeClientError("INVALID_RESPONSE_FRAMING", "Bridge returned invalid framing")
    try:
        response = json.loads(raw[:-1])
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PetRuntimeClientError("MALFORMED_RESPONSE", "Bridge returned invalid JSON") from error
    if not isinstance(response, dict) or set(response) != {"protocolVersion", "requestId", "ok"} | (
        {"result"} if response.get("ok") is True else {"error"}
    ):
        raise PetRuntimeClientError("INVALID_RESPONSE", "Bridge response fields are invalid")
    if response["protocolVersion"] != PROTOCOL_VERSION or response["requestId"] != request_id:
        raise PetRuntimeClientError("RESPONSE_MISMATCH", "Bridge response does not match the request")
    if response["ok"] is False:
        error = response.get("error")
        if not isinstance(error, dict) or set(error) != {"code", "message"} or not all(
            isinstance(error.get(key), str) for key in ("code", "message")
        ):
            raise PetRuntimeClientError("INVALID_RESPONSE", "Bridge error response is invalid")
        raise PetRuntimeClientError(error["code"], error["message"])
    if response["ok"] is not True:
        raise PetRuntimeClientError("INVALID_RESPONSE", "Bridge ok flag is invalid")
    result = response.get("result")
    if not isinstance(result, dict) or set(result) != {"accepted", "currentForm", "targetForm", "transitioning"}:
        raise PetRuntimeClientError("INVALID_RESPONSE", "Bridge result fields are invalid")
    if not isinstance(result["accepted"], bool) or not isinstance(result["transitioning"], bool):
        raise PetRuntimeClientError("INVALID_RESPONSE", "Bridge result types are invalid")
    if result["currentForm"] not in {"gu", "feng"} or result["targetForm"] not in {"gu", "feng"}:
        raise PetRuntimeClientError("INVALID_RESPONSE", "Bridge form is invalid")
    return result


def set_target_form(
    target: str,
    animate: bool = True,
    request_id: str | None = None,
    *,
    socket_path: str | os.PathLike[str] | None = None,
    timeout: float = 2.0,
) -> dict[str, Any]:
    if target not in {"gu", "feng"}:
        raise ValueError("target must be gu or feng")
    if not isinstance(animate, bool):
        raise TypeError("animate must be boolean")
    actual_request_id = request_id or str(uuid.uuid4())
    if not _valid_request_id(actual_request_id):
        raise ValueError("request_id is invalid")
    if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or not 0 < timeout <= 10:
        raise ValueError("timeout must be within (0, 10]")
    destination = Path(socket_path) if socket_path is not None else default_socket_path()
    request = {
        "protocolVersion": PROTOCOL_VERSION,
        "requestId": actual_request_id,
        "method": "setTargetForm",
        "params": {"target": target, "animate": animate},
    }
    wire = json.dumps(request, separators=(",", ":")).encode() + b"\n"
    if len(wire) > MAX_MESSAGE_BYTES + 1:
        raise PetRuntimeClientError("REQUEST_TOO_LARGE", "Bridge request exceeds the message limit")
    chunks: list[bytes] = []
    size = 0
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(float(timeout))
            client.connect(os.fspath(destination))
            client.sendall(wire)
            while True:
                chunk = client.recv(min(1024, MAX_MESSAGE_BYTES + 1 - size))
                if not chunk:
                    raise PetRuntimeClientError("CONNECTION_CLOSED", "Bridge closed without a response")
                chunks.append(chunk)
                size += len(chunk)
                joined = b"".join(chunks)
                if b"\n" in joined:
                    return _parse_response(joined, actual_request_id)
                if size > MAX_MESSAGE_BYTES:
                    raise PetRuntimeClientError("RESPONSE_TOO_LARGE", "Bridge response exceeds the message limit")
    except socket.timeout as error:
        raise PetRuntimeClientError("TIMEOUT", "Bridge request timed out") from error
    except (FileNotFoundError, ConnectionRefusedError) as error:
        raise PetRuntimeClientError("BRIDGE_UNAVAILABLE", "Liang Pet runtime bridge is unavailable") from error
    except OSError as error:
        raise PetRuntimeClientError("BRIDGE_IO_ERROR", "Liang Pet runtime bridge connection failed") from error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    set_form = subparsers.add_parser("set-form", help="send one development setTargetForm request")
    set_form.add_argument("target", choices=("gu", "feng"))
    set_form.add_argument("--no-animate", action="store_true")
    set_form.add_argument("--socket-path", type=Path, default=default_socket_path())
    args = parser.parse_args()
    try:
        result = set_target_form(args.target, not args.no_animate, socket_path=args.socket_path)
    except PetRuntimeClientError as error:
        print(json.dumps({"ok": False, "error": {"code": error.code, "message": str(error)}}))
        return 1
    print(json.dumps({"ok": True, "result": result}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
