from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
from datetime import datetime
from pathlib import Path

import pytest

from tools.pet_runtime_client import set_target_form
from tools.time_form_watcher import BridgeWatcher, runtime_session_identity


class FakeRuntimeBridge:
    """Protocol-v1 test runtime; it models forms, not renderer animation."""

    def __init__(self, socket_path: Path, *, current_form: str = "gu") -> None:
        self.socket_path = socket_path
        self.current_form = current_form
        self.requests: list[dict[str, object]] = []
        self._server: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def start(self) -> None:
        self._stop.clear()
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(os.fspath(self.socket_path))
        os.chmod(self.socket_path, 0o600)
        server.listen()
        server.settimeout(0.05)
        self._server = server
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._server is not None:
            self._server.close()
        if self._thread is not None:
            self._thread.join(timeout=1)
        self._server = None
        self._thread = None
        self.socket_path.unlink(missing_ok=True)

    def _serve(self) -> None:
        assert self._server is not None
        while not self._stop.is_set():
            try:
                connection, _ = self._server.accept()
            except (TimeoutError, OSError):
                continue
            with connection:
                wire = b""
                while b"\n" not in wire:
                    chunk = connection.recv(4096)
                    if not chunk:
                        break
                    wire += chunk
                request = json.loads(wire.rstrip(b"\n"))
                params = request["params"]
                target = params["target"]
                animate = params["animate"]
                self.requests.append(request)
                self.current_form = target
                response = {
                    "protocolVersion": 1,
                    "requestId": request["requestId"],
                    "ok": True,
                    "result": {
                        "accepted": True,
                        "currentForm": target,
                        "targetForm": target,
                        "transitioning": animate,
                    },
                }
                connection.sendall(
                    json.dumps(response, separators=(",", ":")).encode() + b"\n"
                )


@pytest.fixture
def socket_root():
    with tempfile.TemporaryDirectory(prefix="l5-e2e-", dir=tempfile.gettempdir()) as root:
        yield Path(root)


def make_watcher(socket_path: Path) -> BridgeWatcher:
    sequence = iter(f"e2e-{index}" for index in range(100))
    return BridgeWatcher(
        client=lambda target, **kwargs: set_target_form(
            target, socket_path=socket_path, timeout=1, **kwargs
        ),
        session_probe=lambda: runtime_session_identity(socket_path),
        request_id_factory=lambda: next(sequence),
    )


def pairs(runtime: FakeRuntimeBridge) -> list[tuple[str, bool]]:
    return [
        (request["params"]["target"], request["params"]["animate"])  # type: ignore[index]
        for request in runtime.requests
    ]


def test_case_a_full_monday_schedule(socket_root: Path) -> None:
    runtime = FakeRuntimeBridge(socket_root / "runtime.sock")
    runtime.start()
    try:
        watcher = make_watcher(runtime.socket_path)
        for value in (
            "2026-01-05T08:30:00",
            "2026-01-05T09:00:00",
            "2026-01-05T12:00:00",
            "2026-01-05T14:00:00",
            "2026-01-05T18:00:00",
        ):
            watcher.attempt(datetime.fromisoformat(value))
        assert pairs(runtime) == [
            ("gu", False),
            ("feng", True),
            ("gu", True),
            ("feng", True),
            ("gu", True),
        ]
    finally:
        runtime.stop()


def test_case_b_friday_to_weekend_has_no_repeat(socket_root: Path) -> None:
    runtime = FakeRuntimeBridge(socket_root / "runtime.sock", current_form="feng")
    runtime.start()
    try:
        watcher = make_watcher(runtime.socket_path)
        watcher.attempt(datetime.fromisoformat("2026-01-09T17:59:00"))
        watcher.attempt(datetime.fromisoformat("2026-01-09T18:00:00"))
        weekend = watcher.attempt(datetime.fromisoformat("2026-01-10T12:00:00"))
        assert pairs(runtime) == [("feng", False), ("gu", True)]
        assert weekend.sent is False
    finally:
        runtime.stop()


def test_case_c_late_runtime_reconciles_current_without_backfill(socket_root: Path) -> None:
    socket_path = socket_root / "runtime.sock"
    watcher = make_watcher(socket_path)
    unavailable = watcher.attempt(datetime.fromisoformat("2026-01-05T09:00:00"))
    assert unavailable.error_code == "BRIDGE_UNAVAILABLE"

    runtime = FakeRuntimeBridge(socket_path)
    runtime.start()
    try:
        recovered = watcher.attempt(datetime.fromisoformat("2026-01-05T09:07:00"))
        assert (recovered.accepted, recovered.animate) == (True, False)
        assert pairs(runtime) == [("feng", False)]
    finally:
        runtime.stop()


def test_case_d_sleep_1130_to_1430_does_not_backfill(socket_root: Path) -> None:
    runtime = FakeRuntimeBridge(socket_root / "runtime.sock")
    runtime.start()
    try:
        watcher = make_watcher(runtime.socket_path)
        watcher.attempt(datetime.fromisoformat("2026-01-05T11:30:00"))
        wake = watcher.attempt(datetime.fromisoformat("2026-01-05T14:30:00"))
        assert pairs(runtime) == [("feng", False)]
        assert wake.sent is False
    finally:
        runtime.stop()


def test_case_e_runtime_restart_reconciles_without_animation(socket_root: Path) -> None:
    socket_path = socket_root / "runtime.sock"
    old_runtime = FakeRuntimeBridge(socket_path)
    old_runtime.start()
    watcher = make_watcher(socket_path)
    watcher.attempt(datetime.fromisoformat("2026-01-05T10:00:00"))
    assert pairs(old_runtime) == [("feng", False)]
    old_runtime.stop()

    new_runtime = FakeRuntimeBridge(socket_path)
    new_runtime.start()
    try:
        reconciled = watcher.attempt(datetime.fromisoformat("2026-01-05T10:15:00"))
        assert (reconciled.accepted, reconciled.animate) == (True, False)
        assert pairs(new_runtime) == [("feng", False)]
    finally:
        new_runtime.stop()


def test_case_f_normal_live_boundary_animates(socket_root: Path) -> None:
    runtime = FakeRuntimeBridge(socket_root / "runtime.sock")
    runtime.start()
    try:
        watcher = make_watcher(runtime.socket_path)
        watcher.attempt(datetime.fromisoformat("2026-01-05T08:59:00"))
        boundary = watcher.attempt(datetime.fromisoformat("2026-01-05T09:00:00"))
        assert boundary.animate is True
        assert pairs(runtime) == [("gu", False), ("feng", True)]
    finally:
        runtime.stop()


def test_no_legacy_mutation_guard(socket_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_home = socket_root / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", os.fspath(fake_home))
    runtime = FakeRuntimeBridge(socket_root / "runtime.sock")
    runtime.start()
    try:
        watcher = make_watcher(runtime.socket_path)
        watcher.attempt(datetime.fromisoformat("2026-01-05T09:00:00"))
        assert list(fake_home.rglob("*")) == []
        assert runtime.socket_path != fake_home / ".codex" / "ipc" / "ipc.sock"
        source = (Path(__file__).parents[1] / "tools" / "time_form_watcher.py").read_text()
        assert "refresh_required" not in source
        assert "Settings > Pets > Refresh" not in source
        assert "spritesheet.webp" not in source
    finally:
        runtime.stop()
