#!/usr/bin/env python3
"""Synthetic metadata replay through the real receiver and Electron window.

This is NOT a Codex Desktop event test. It verifies only the project-owned
receiver -> App -> animation path before live Desktop QA.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.run_electron_harness import LiveHarness
from tools.run_standalone_app_qa import APP, ELECTRON, ROOT, wait_event


def send_event(socket_path: Path, name: str, offset: int) -> None:
    payload = {"event": name, "session_id": "synthetic-replay",
               "timestamp": f"2026-09-26T10:00:{offset:02d}.000+00:00"}
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(1)
        client.connect(str(socket_path))
        client.sendall((json.dumps(payload) + "\n").encode())


def run(output: Path, executable: Path = ELECTRON) -> dict[str, object]:
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="lnh-replay-", dir="/tmp") as temporary:
        root = Path(temporary)
        for name in ("home", "tmp", "user-data", "project/.cache"):
            (root / name).mkdir(parents=True)
        environment = {
            "HOME": str(root / "home"), "TMPDIR": str(root / "tmp") + os.sep,
            "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin"),
            "LANG": "en_US.UTF-8", "LNH_STANDALONE_TEST": "1",
            "LNH_STANDALONE_TEST_ROOT": str(root),
            "LNH_HOOK_PROJECT_ROOT": str(root / "project"),
            "LNH_TEST_INITIAL_TIME": "2026-09-14T08:59:00+08:00",
        }
        process = subprocess.Popen([str(executable), str(APP)], cwd=ROOT, env=environment,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, bufsize=1)
        live = LiveHarness(process)
        hook_socket = root / "project/.cache/codex-events.sock"
        try:
            wait_event(live, lambda item: item.get("type") == "startup", timeout=30)
            deadline = time.monotonic() + 5
            while not hook_socket.is_socket() and time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError(f"App exited before receiver: {process.returncode}")
                time.sleep(0.025)
            if not hook_socket.is_socket():
                raise RuntimeError(f"project Hook receiver did not start; events={live.events[-6:]}; "
                                   f"stderr={live.stderr_lines[-3:]}")
            send_event(hook_socket, "SessionStart", 0)
            wait_event(live, lambda item: item.get("type") == "hook-event"
                       and item.get("hookEvent") == "SessionStart")
            send_event(hook_socket, "PreToolUse", 1)
            wait_event(live, lambda item: item.get("type") == "renderer"
                       and item.get("state") == "running" and item.get("row") == 7)
            send_event(hook_socket, "PostToolUse", 2)
            wait_event(live, lambda item: item.get("type") == "hook-event"
                       and item.get("hookEvent") == "PostToolUse")
            if not any(item.get("type") == "state" and item.get("normalState") == "running"
                       for item in live.events):
                raise RuntimeError("PostToolUse prematurely ended Running")
            live.send(type="form", form="feng")
            first = wait_event(live, lambda item: item.get("type") == "transition-complete"
                               and item.get("transitionId") == "gu_to_feng", timeout=12)
            if first.get("underlyingState") != "running":
                raise RuntimeError("Gu→Feng lost Running state")
            live.send(type="form", form="gu")
            second = wait_event(live, lambda item: item.get("type") == "transition-complete"
                                and item.get("transitionId") == "feng_to_gu", timeout=12)
            if second.get("underlyingState") != "running":
                raise RuntimeError("Feng→Gu lost Running state")
            send_event(hook_socket, "Stop", 3)
            wait_event(live, lambda item: item.get("type") == "renderer"
                       and item.get("state") == "idle" and item.get("row") == 0)
            result = {"status": "SYNTHETIC_REPLAY_PASS", "desktopEventsVerified": False,
                      "receiverToRenderer": True, "bidirectionalTransitionRestoredRunning": True,
                      "stopRestoredIdle": True, "events": len(live.events)}
            (output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
            return result
        finally:
            if process.poll() is None:
                try:
                    live.send(type="quit")
                    process.wait(timeout=5)
                except (BrokenPipeError, subprocess.TimeoutExpired):
                    process.terminate()
                    process.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "standalone-app/evidence/hook-replay")
    args = parser.parse_args()
    print(json.dumps(run(args.output), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
