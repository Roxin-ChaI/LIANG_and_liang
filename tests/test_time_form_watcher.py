from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from tools.pet_runtime_client import PetRuntimeClientError
from tools.time_form_watcher import BridgeWatcher, dry_run, watch


ROOT = Path(__file__).resolve().parents[1]
WATCHER = ROOT / "tools" / "time_form_watcher.py"


class FakeRuntime:
    def __init__(self, session: str | None = "session-1") -> None:
        self.session = session
        self.calls: list[tuple[str, bool, str]] = []
        self.failures = 0
        self.malformed = False

    def probe(self) -> object | None:
        return self.session

    def client(self, target: str, *, animate: bool, request_id: str):
        self.calls.append((target, animate, request_id))
        if self.failures:
            self.failures -= 1
            raise PetRuntimeClientError("BRIDGE_UNAVAILABLE", "unavailable")
        if self.malformed:
            raise PetRuntimeClientError("INVALID_RESPONSE", "invalid response")
        return {
            "accepted": True,
            "currentForm": target,
            "targetForm": target,
            "transitioning": animate,
        }


def make_watcher(runtime: FakeRuntime) -> BridgeWatcher:
    counter = iter(f"request-{index}" for index in range(100))
    return BridgeWatcher(
        client=runtime.client,
        session_probe=runtime.probe,
        request_id_factory=lambda: next(counter),
    )


@pytest.mark.parametrize(
    ("value", "target"),
    [("2026-01-05T08:30:00", "gu"), ("2026-01-05T10:00:00", "feng")],
)
def test_startup_reconcile_is_not_animated(value: str, target: str) -> None:
    runtime = FakeRuntime()
    event = make_watcher(runtime).attempt(datetime.fromisoformat(value))
    assert (event.accepted, event.animate) == (True, False)
    assert runtime.calls[0][:2] == (target, False)


@pytest.mark.parametrize(
    ("before", "boundary", "first", "second"),
    [
        ("2026-01-05T08:59:00", "2026-01-05T09:00:00", "gu", "feng"),
        ("2026-01-05T11:59:00", "2026-01-05T12:00:00", "feng", "gu"),
        ("2026-01-05T13:59:00", "2026-01-05T14:00:00", "gu", "feng"),
        ("2026-01-05T17:59:00", "2026-01-05T18:00:00", "feng", "gu"),
    ],
)
def test_real_boundaries_animate(
    before: str, boundary: str, first: str, second: str
) -> None:
    runtime = FakeRuntime()
    bridge = make_watcher(runtime)
    bridge.attempt(datetime.fromisoformat(before))
    event = bridge.attempt(datetime.fromisoformat(boundary))
    assert runtime.calls == [
        (first, False, "request-0"),
        (second, True, "request-1"),
    ]
    assert (event.accepted, event.animate) == (True, True)


def test_weekend_startup_and_duplicate_success() -> None:
    runtime = FakeRuntime()
    bridge = make_watcher(runtime)
    first = bridge.attempt(datetime(2026, 1, 10, 10, 0))
    second = bridge.attempt(datetime(2026, 1, 11, 10, 0))
    assert first.accepted is True
    assert second.sent is False
    assert [call[:2] for call in runtime.calls] == [("gu", False)]


def test_bridge_unavailable_does_not_acknowledge() -> None:
    runtime = FakeRuntime(session=None)
    runtime.failures = 1
    bridge = make_watcher(runtime)
    event = bridge.attempt(datetime(2026, 1, 5, 10, 0))
    assert event.error_code == "BRIDGE_UNAVAILABLE"
    assert bridge.scheduler.last_acknowledged_form is None


def test_exponential_retry_and_cap() -> None:
    runtime = FakeRuntime(session=None)
    runtime.failures = 20
    bridge = make_watcher(runtime)
    delays = [bridge.attempt(datetime(2026, 1, 5, 10, 0)).retry_after for _ in range(10)]
    assert delays == [1, 2, 4, 8, 15, 30, 60, 60, 60, 60]


def test_recovery_after_unavailable_is_non_animated_reconcile() -> None:
    runtime = FakeRuntime(session=None)
    runtime.failures = 1
    bridge = make_watcher(runtime)
    bridge.attempt(datetime(2026, 1, 5, 9, 0))
    runtime.session = "session-late"
    event = bridge.attempt(datetime(2026, 1, 5, 9, 7))
    assert (event.accepted, event.animate) == (True, False)
    assert [call[:2] for call in runtime.calls] == [("feng", False), ("feng", False)]


def test_no_historical_backfill_after_multiple_nodes() -> None:
    runtime = FakeRuntime()
    bridge = make_watcher(runtime)
    bridge.attempt(datetime(2026, 1, 5, 8, 59))
    bridge.attempt(datetime(2026, 1, 5, 15, 0))
    assert [call[:2] for call in runtime.calls] == [("gu", False), ("feng", True)]


def test_sleep_across_one_transition_uses_current_form_only() -> None:
    runtime = FakeRuntime()
    bridge = make_watcher(runtime)
    bridge.attempt(datetime(2026, 1, 5, 11, 30))
    bridge.attempt(datetime(2026, 1, 5, 12, 30))
    assert [call[:2] for call in runtime.calls] == [("feng", False), ("gu", True)]


def test_sleep_across_multiple_transitions_same_expected_is_no_op() -> None:
    runtime = FakeRuntime()
    bridge = make_watcher(runtime)
    bridge.attempt(datetime(2026, 1, 5, 11, 30))
    event = bridge.attempt(datetime(2026, 1, 5, 14, 30))
    assert event.sent is False
    assert [call[:2] for call in runtime.calls] == [("feng", False)]


def test_runtime_restart_forces_non_animated_reconcile() -> None:
    runtime = FakeRuntime("session-old")
    bridge = make_watcher(runtime)
    bridge.attempt(datetime(2026, 1, 5, 10, 0))
    runtime.session = "session-new"
    event = bridge.attempt(datetime(2026, 1, 5, 10, 30))
    assert (event.accepted, event.animate) == (True, False)
    assert [call[:2] for call in runtime.calls] == [("feng", False), ("feng", False)]


def test_not_accepted_and_malformed_do_not_acknowledge() -> None:
    runtime = FakeRuntime()
    runtime.client = lambda *args, **kwargs: {
        "accepted": False,
        "currentForm": "gu",
        "targetForm": "feng",
        "transitioning": False,
    }
    bridge = make_watcher(runtime)
    assert bridge.attempt(datetime(2026, 1, 5, 10, 0)).error_code == "NOT_ACCEPTED"
    assert bridge.scheduler.last_acknowledged_form is None

    malformed = FakeRuntime()
    malformed.malformed = True
    malformed_bridge = make_watcher(malformed)
    assert malformed_bridge.attempt(datetime(2026, 1, 5, 10, 0)).error_code == "INVALID_RESPONSE"
    assert malformed_bridge.scheduler.last_acknowledged_form is None


def test_watch_uses_retry_wait_then_recovers() -> None:
    runtime = FakeRuntime(session=None)
    runtime.failures = 1
    bridge = make_watcher(runtime)
    times = iter([datetime(2026, 1, 5, 10, 0)] * 4)
    sleeps: list[float] = []

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        runtime.session = "session-available"

    events = []
    watch(
        clock=lambda: next(times),
        sleeper=sleep,
        bridge=bridge,
        on_event=events.append,
        max_iterations=2,
    )
    assert sleeps == [1.0]
    assert [event.accepted for event in events] == [False, True]


def test_ctrl_c_is_clean(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    import tools.time_form_watcher as module

    def interrupt(**_kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(module, "watch", interrupt)
    monkeypatch.setattr(sys, "argv", [str(WATCHER)])
    assert module.main() == 0
    assert capsys.readouterr().out.strip() == "stopped=true"


def test_dry_run_has_no_bridge_or_legacy_output() -> None:
    lines: list[str] = []
    dry_run(datetime(2026, 1, 5, 8, 30), lines.append)
    output = "\n".join(lines)
    assert "current_time=2026-01-05T08:30:00+08:00" in output
    assert "expected_form=gu" in output
    assert "next_transition=2026-01-05T09:00:00+08:00" in output
    assert "dry_run=true" in output
    assert "refresh_required" not in output


def test_cli_dry_run_smoke() -> None:
    completed = subprocess.run(
        [sys.executable, str(WATCHER), "--dry-run", "--at", "2026-01-05T08:30:00"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "expected_form=gu" in completed.stdout
    assert "dry_run=true" in completed.stdout


def test_production_watcher_has_no_legacy_mutation_or_refresh_text() -> None:
    source = WATCHER.read_text()
    for forbidden in (
        "shutil.copy",
        "os.replace",
        "spritesheet.webp",
        "refresh_required",
        "Settings > Pets > Refresh",
        ".codex/pets",
    ):
        assert forbidden not in source
    assert "private ipc.sock" not in source
