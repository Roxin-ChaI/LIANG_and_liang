import datetime as dt
import importlib.util
import json
from pathlib import Path
import sys
import time

import pytest


ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "tools" / "codex_hook_probe.py"
RECEIVER = ROOT / "tools" / "codex_hook_receiver.py"
spec = importlib.util.spec_from_file_location("codex_hook_probe", HOOK)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def test_metadata_whitelist_discards_sensitive_content():
    fixed = dt.datetime(2026, 9, 26, tzinfo=dt.timezone.utc)
    value = probe.metadata({"hook_event_name": "PreToolUse", "session_id": "s-1",
                            "prompt": "SECRET", "tool_input": {"password": "SECRET"},
                            "tool_output": "SECRET", "transcript_path": "/private/SECRET"}, fixed)
    assert value == {"event": "PreToolUse", "session_id": "s-1",
                     "timestamp": "2026-09-26T00:00:00.000+00:00"}
    assert "SECRET" not in json.dumps(value)


def test_unknown_event_ignored():
    assert probe.metadata({"hook_event_name": "Other", "session_id": "s"}) is None


def test_no_listener_connect_fails_fast(tmp_path):
    started = time.monotonic()
    with pytest.raises(OSError):
        probe.deliver({"event": "Stop", "session_id": "s", "timestamp": "t"},
                      str(tmp_path / "missing.sock"))
    assert time.monotonic() - started < 1


def test_main_stays_fail_open_when_diagnostic_and_socket_fail(monkeypatch, tmp_path):
    from io import BytesIO, TextIOWrapper

    payload = json.dumps({"hook_event_name": "Stop", "session_id": "s", "prompt": "SECRET"})
    monkeypatch.setattr(sys, "stdin", TextIOWrapper(BytesIO(payload.encode())))

    def fail_diagnostic(_event):
        raise OSError("diagnostic unavailable")

    monkeypatch.setattr(probe, "write_diagnostic", fail_diagnostic)
    assert probe.main([str(tmp_path / "missing.sock")]) == 0


def test_diagnostic_is_private_metadata_only(tmp_path):
    destination = tmp_path / "entry.jsonl"
    event = {"event": "PreToolUse", "session_id": "desktop-1", "timestamp": "2026-09-26T00:00:00Z",
             "prompt": "SECRET", "tool_input": "SECRET"}
    probe.write_diagnostic(event, destination, pid=123)
    assert destination.stat().st_mode & 0o777 == 0o600
    assert json.loads(destination.read_text()) == {
        "event": "PreToolUse", "timestamp": "2026-09-26T00:00:00Z", "pid": 123,
        "session_id": "desktop-1"}
    assert "SECRET" not in destination.read_text()


def test_diagnostic_refuses_symlink(tmp_path):
    original = tmp_path / "original"
    original.write_text("unchanged")
    link = tmp_path / "entry.jsonl"
    link.symlink_to(original)
    with pytest.raises(OSError):
        probe.write_diagnostic({"event": "Stop", "session_id": "s", "timestamp": "t"}, link)
    assert original.read_text() == "unchanged"


def test_receiver_rejects_extra_fields():
    sys.path.insert(0, str(ROOT / "tools"))
    from codex_hook_receiver import accept_metadata
    assert accept_metadata({"event": "Stop", "session_id": "s", "timestamp": "t",
                            "prompt": "SECRET"}) is None


def test_receiver_forwards_only_minimized_metadata(monkeypatch, tmp_path):
    sys.path.insert(0, str(ROOT / "tools"))
    import codex_hook_receiver as receiver

    recorded = []

    class FakeSocket:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def settimeout(self, timeout):
            assert timeout == 0.05

        def connect(self, destination):
            recorded.append(destination)

        def sendall(self, wire):
            recorded.append(json.loads(wire))

    monkeypatch.setattr(receiver.socket, "socket", lambda *_args: FakeSocket())
    value = {"event": "PreToolUse", "session_id": "desktop", "timestamp": "t"}
    destination = tmp_path / "forward.sock"
    assert receiver.forward_metadata(value, destination) is True
    assert recorded == [str(destination), value]
    assert receiver.forward_metadata(value, None) is False


def test_receiver_pipeline_trace_is_private_and_metadata_only(tmp_path):
    sys.path.insert(0, str(ROOT / "tools"))
    import codex_hook_receiver as receiver

    destination = tmp_path / "forward-diagnostic.jsonl"
    event = {"event": "PreToolUse", "session_id": "desktop-1", "timestamp": "t",
             "tool_input": "SECRET"}
    receiver.write_pipeline_diagnostic(destination, "python-forwarded", event, False)
    saved = destination.read_text()
    assert destination.stat().st_mode & 0o777 == 0o600
    assert "SECRET" not in saved
    assert json.loads(saved)["success"] is False
    assert json.loads(saved)["stage"] == "python-forwarded"


def test_receiver_pipeline_trace_refuses_symlink(tmp_path):
    sys.path.insert(0, str(ROOT / "tools"))
    import codex_hook_receiver as receiver

    target = tmp_path / "target"
    target.write_text("unchanged")
    link = tmp_path / "diagnostic.jsonl"
    link.symlink_to(target)
    receiver.write_pipeline_diagnostic(link, "python-received",
                                       {"event": "Stop", "session_id": "s"})
    assert target.read_text() == "unchanged"
