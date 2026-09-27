#!/usr/bin/env python3
"""Live, project-owned Electron playback audit (no Codex or asset writes)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.run_electron_harness import LiveHarness
from tools.run_standalone_app_qa import APP, ELECTRON, ROOT, command, wait_event


def unexpected_restart(events: list[dict], *, after: int) -> bool:
    """A duplicate Running event must not send the playhead back to frame zero."""
    return any(event.get("type") == "renderer" and event.get("row") == 7
               and event.get("frame") == 0 for event in events[after:])


def audit(output: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="liang-animation-audit-") as temporary:
        test_root = Path(temporary)
        for name in ("home", "tmp", "user-data"):
            (test_root / name).mkdir()
        env = {
            "HOME": str(test_root / "home"), "TMPDIR": str(test_root / "tmp") + os.sep,
            "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin"),
            "LANG": "en_US.UTF-8", "LNH_STANDALONE_TEST": "1",
            "LNH_DISABLE_CODEX_EVENTS": "1", "LNH_STANDALONE_TEST_ROOT": str(test_root),
            "LNH_TEST_INITIAL_TIME": "2026-09-14T08:30:00+08:00",
        }
        process = subprocess.Popen([str(ELECTRON), str(APP)], cwd=ROOT, env=env,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, bufsize=1)
        live = LiveHarness(process)
        try:
            wait_event(live, lambda e: e.get("type") == "startup", timeout=30)
            command(live, type="move", x=20, y=20)
            command(live, type="interaction", kind="hover", value=False)
            command(live, type="interaction", kind="look", value=None)
            begin = command(live, type="work", state="running")
            wait_event(live, lambda e: e.get("type") == "renderer"
                       and e.get("row") == 7 and e.get("frame") == 2, after=begin)
            duplicate = command(live, type="work", state="running")
            time.sleep(0.08)
            restart = unexpected_restart(live.events, after=duplicate)
            command(live, type="work", state="idle")
            report = {
                "app": "project-owned standalone Electron",
                "duplicateRunningRestartedFrameZero": restart,
                "verdict": "FAIL" if restart else "PASS",
                "steps": ["enter Running", "observe frame 2", "repeat Running", "inspect next 80 ms"],
                "events": [event for event in live.events if event.get("type") in ("state", "renderer")],
            }
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(report, indent=2) + "\n")
            return report
        finally:
            if process.poll() is None:
                live.send(type="quit")
                process.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.output)
    print(json.dumps({"verdict": result["verdict"], "report": str(args.output)}))
    return 0 if result["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
