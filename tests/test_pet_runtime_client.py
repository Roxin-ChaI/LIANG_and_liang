from __future__ import annotations

import json
import socket
import threading
import time
import tempfile
import uuid
from pathlib import Path

import pytest

from tools.pet_runtime_client import PetRuntimeClientError, set_target_form


@pytest.fixture
def short_socket():
    """macOS sockaddr_un is shorter than pytest's descriptive tmp_path."""
    path = Path(tempfile.gettempdir()) / f"l4-{uuid.uuid4().hex[:10]}.sock"
    yield path
    path.unlink(missing_ok=True)


def response(request: dict, **overrides: object) -> dict:
    value = {
        "protocolVersion": 1,
        "requestId": request["requestId"],
        "ok": True,
        "result": {
            "accepted": True,
            "currentForm": request["params"]["target"],
            "targetForm": request["params"]["target"],
            "transitioning": request["params"]["animate"],
        },
    }
    value.update(overrides)
    return value


class FakeServer:
    def __init__(self, path: Path, handler) -> None:
        self.path = path
        self.handler = handler
        self.request = None
        self.error = None
        self.ready = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def __enter__(self):
        self.thread.start()
        assert self.ready.wait(1)
        return self

    def __exit__(self, exc_type, exc, tb):
        self.thread.join(2)
        if self.error and exc is None:
            raise self.error

    def _run(self):
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
                server.bind(str(self.path))
                server.listen(1)
                self.ready.set()
                connection, _ = server.accept()
                with connection:
                    raw = b""
                    while not raw.endswith(b"\n"):
                        raw += connection.recv(4096)
                    self.request = json.loads(raw)
                    wire = self.handler(self.request)
                    if wire is not None:
                        connection.sendall(wire if isinstance(wire, bytes) else json.dumps(wire).encode() + b"\n")
        except Exception as error:  # surfaced on context exit
            self.error = error
            self.ready.set()


def test_gu_request(short_socket):
    path = short_socket
    with FakeServer(path, response) as server:
        result = set_target_form("gu", socket_path=path)
    assert result["currentForm"] == "gu"
    assert server.request["method"] == "setTargetForm"


def test_feng_request(short_socket):
    path = short_socket
    with FakeServer(path, response):
        assert set_target_form("feng", socket_path=path)["targetForm"] == "feng"


@pytest.mark.parametrize("animate", [True, False])
def test_animate_value_is_exact(short_socket, animate):
    path = short_socket
    with FakeServer(path, response) as server:
        set_target_form("feng", animate=animate, socket_path=path)
    assert server.request["params"]["animate"] is animate


def test_generated_request_id_is_uuid_shaped(short_socket):
    path = short_socket
    with FakeServer(path, response) as server:
        set_target_form("gu", socket_path=path)
    assert len(server.request["requestId"]) == 36
    assert server.request["requestId"].count("-") == 4


def test_explicit_request_id_round_trips(short_socket):
    path = short_socket
    with FakeServer(path, response):
        set_target_form("gu", request_id="known-id", socket_path=path)


def test_timeout_is_not_swallowed(short_socket):
    path = short_socket

    def delayed(_):
        time.sleep(0.15)
        return None

    with FakeServer(path, delayed):
        with pytest.raises(PetRuntimeClientError, match="timed out") as raised:
            set_target_form("gu", socket_path=path, timeout=0.03)
    assert raised.value.code == "TIMEOUT"


def test_malformed_response(short_socket):
    path = short_socket
    with FakeServer(path, lambda _: b"not-json\n"):
        with pytest.raises(PetRuntimeClientError) as raised:
            set_target_form("gu", socket_path=path)
    assert raised.value.code == "MALFORMED_RESPONSE"


def test_mismatched_request_id(short_socket):
    path = short_socket

    def mismatch(request):
        value = response(request)
        value["requestId"] = "different"
        return value

    with FakeServer(path, mismatch):
        with pytest.raises(PetRuntimeClientError) as raised:
            set_target_form("gu", request_id="expected", socket_path=path)
    assert raised.value.code == "RESPONSE_MISMATCH"


def test_server_error_is_preserved(short_socket):
    path = short_socket

    def rejected(request):
        return {
            "protocolVersion": 1,
            "requestId": request["requestId"],
            "ok": False,
            "error": {"code": "RUNTIME_NOT_READY", "message": "Pet runtime is not ready"},
        }

    with FakeServer(path, rejected):
        with pytest.raises(PetRuntimeClientError) as raised:
            set_target_form("feng", socket_path=path)
    assert raised.value.code == "RUNTIME_NOT_READY"


def test_unavailable_socket_has_no_fallback(short_socket):
    missing = short_socket
    parent = missing.parent
    before = set(parent.iterdir())
    with pytest.raises(PetRuntimeClientError) as raised:
        set_target_form("feng", socket_path=missing)
    assert raised.value.code == "BRIDGE_UNAVAILABLE"
    assert set(parent.iterdir()) == before


def test_extra_response_fields_rejected(short_socket):
    path = short_socket

    def extra(request):
        value = response(request)
        value["result"]["path"] = "/tmp/atlas.webp"
        return value

    with FakeServer(path, extra):
        with pytest.raises(PetRuntimeClientError) as raised:
            set_target_form("gu", socket_path=path)
    assert raised.value.code == "INVALID_RESPONSE"
