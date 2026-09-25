import datetime as dt
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time


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


def test_no_listener_is_fast_and_fail_open(tmp_path):
    started = time.monotonic()
    result = subprocess.run([sys.executable, str(HOOK), str(tmp_path / "missing.sock")],
                            input=json.dumps({"hook_event_name": "Stop", "session_id": "s",
                                              "prompt": "SECRET"}), text=True, capture_output=True,
                            timeout=2, check=False)
    assert result.returncode == 0
    assert result.stdout == result.stderr == ""
    assert time.monotonic() - started < 1


def test_receiver_rejects_extra_fields():
    sys.path.insert(0, str(ROOT / "tools"))
    from codex_hook_receiver import accept_metadata
    assert accept_metadata({"event": "Stop", "session_id": "s", "timestamp": "t",
                            "prompt": "SECRET"}) is None
