#!/usr/bin/env python3
"""Observe real Desktop Hooks driving the project-owned Electron App.

No events are injected. The caller starts an actual Codex Desktop tool task
after this script prints LIVE_HOOK_QA_READY, then performs a real mouse drag
after DRAG_READY. The script retains only metadata and renderer telemetry.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.run_electron_harness import LiveHarness
from tools.run_standalone_app_qa import ROOT, wait_event


DEFAULT_APP = ROOT / "dist/Liang no Henshin Phase2 Live Preloaded.app/Contents/MacOS/Electron"
SAFE_TYPES = {"startup", "overlay-preloaded", "hook-receiver-started", "hook-event", "state", "renderer",
              "transition-complete", "window-position", "capture", "quit"}


def captured_frames(events: list[dict], name: str, after: int) -> list[int]:
    return sorted({event["transitionFrame"] for event in events[after:]
                   if event.get("type") == "renderer" and event.get("transitionId") == name
                   and isinstance(event.get("transitionFrame"), int)})


def latency(hook: dict, rendered: dict) -> int:
    timestamp = datetime.fromisoformat(str(hook["hookTimestamp"]).replace("Z", "+00:00"))
    return round(rendered["observedAt"] - timestamp.timestamp() * 1000)


def run(executable: Path, output: Path, session_id: str, drag_timeout: float,
        hook_timeout: float) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="lnh-live-", dir="/tmp") as temporary:
        root = Path(temporary)
        for name in ("home", "tmp", "user-data"):
            (root / name).mkdir()
        environment = {
            "HOME": str(root / "home"), "TMPDIR": str(root / "tmp") + os.sep,
            "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin"),
            "LANG": "en_US.UTF-8", "LNH_STANDALONE_TEST": "1",
            "LNH_STANDALONE_TEST_ROOT": str(root),
            "LNH_HOOK_PROJECT_ROOT": str(ROOT),
            "LNH_TEST_HOOK_SESSION": session_id,
            "LNH_TEST_INITIAL_TIME": "2026-09-14T08:59:00+08:00",
        }
        process = subprocess.Popen([str(executable)], cwd=ROOT, env=environment,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, bufsize=1)
        live = LiveHarness(process)
        report = {"desktopSessionId": session_id, "source": "REAL_CODEX_DESKTOP",
                  "restart": "RESTART_NOT_VERIFIED", "physicalMouseDrag": "NOT_VERIFIED"}
        try:
            startup = wait_event(live, lambda item: item.get("type") == "startup", timeout=30)
            if startup.get("initialForm") != "gu":
                raise RuntimeError("test App did not start as Gu")
            preloaded = wait_event(live, lambda item: item.get("type") == "overlay-preloaded")
            if preloaded.get("count") != 18:
                raise RuntimeError("transition overlay frames were not all decoded before startup")
            wait_event(live, lambda item: item.get("type") == "hook-receiver-started", timeout=5)
            hook_socket = ROOT / ".cache/codex-events.sock"
            deadline = time.monotonic() + 5
            while not hook_socket.is_socket() and time.monotonic() < deadline:
                time.sleep(0.025)
            if not hook_socket.is_socket():
                raise RuntimeError(f"Hook receiver unavailable: {live.events[-5:]}")
            print("LIVE_HOOK_QA_READY", flush=True)
            before = len(live.events)
            started = wait_event(live, lambda item: item.get("type") == "hook-event"
                                 and item.get("hookEvent") == "PreToolUse"
                                 and item.get("sessionId") == session_id, after=before, timeout=hook_timeout)
            running = wait_event(live, lambda item: item.get("type") == "renderer"
                                 and item.get("state") == "running" and item.get("row") == 7,
                                 after=before)
            report["running"] = {"result": "PASS", "latencyMs": latency(started, running)}
            before = len(live.events)
            live.send(type="form", form="feng")
            first = wait_event(live, lambda item: item.get("type") == "transition-complete"
                               and item.get("transitionId") == "gu_to_feng", after=before, timeout=12)
            frames_a = captured_frames(live.events, "gu_to_feng", before)
            if first.get("underlyingState") != "running" or frames_a != list(range(10)):
                raise RuntimeError(f"Gu→Feng lost Running or frames: {frames_a}, {first}")
            before = len(live.events)
            live.send(type="form", form="gu")
            second = wait_event(live, lambda item: item.get("type") == "transition-complete"
                                and item.get("transitionId") == "feng_to_gu", after=before, timeout=12)
            frames_b = captured_frames(live.events, "feng_to_gu", before)
            if second.get("underlyingState") != "running" or frames_b != list(range(8)):
                raise RuntimeError(f"Feng→Gu lost Running or frames: {frames_b}, {second}")
            report["transitions"] = {"result": "PASS", "guToFengFrames": frames_a,
                                     "fengToGuFrames": frames_b, "restoredState": "running"}
            stopped = wait_event(live, lambda item: item.get("type") == "hook-event"
                                 and item.get("hookEvent") == "Stop"
                                 and item.get("sessionId") == session_id, after=before, timeout=hook_timeout)
            idle = wait_event(live, lambda item: item.get("type") == "renderer"
                              and item.get("state") == "idle" and item.get("row") == 0,
                              after=before)
            report["idle"] = {"result": "PASS", "latencyMs": latency(stopped, idle)}
            live.send(type="move", x=300, y=300)
            moved = wait_event(live, lambda item: item.get("type") == "window-position"
                               and item.get("bounds", {}).get("x") == 300)
            print(f"DRAG_READY x={moved['bounds']['x']} y={moved['bounds']['y']}", flush=True)
            drag_start = len(live.events)
            try:
                actual = wait_event(live, lambda item: item.get("type") == "window-position"
                                    and item.get("bounds", {}).get("x") != 300,
                                    after=drag_start, timeout=drag_timeout)
                if not any(item.get("type") == "state"
                           and item.get("normalState") in ("running-left", "running-right")
                           for item in live.events[drag_start:]):
                    raise RuntimeError("window moved but drag animation was not observed")
                report["physicalMouseDrag"] = {"result": "PASS", "fromX": 300,
                                               "toX": actual["bounds"]["x"]}
            except Exception as error:
                report["physicalMouseDrag"] = {"result": "NOT_VERIFIED", "reason": str(error)}
            report["status"] = ("LIVE_DESKTOP_HOOK_QA_PASS"
                                if report["physicalMouseDrag"] != "NOT_VERIFIED"
                                and report["physicalMouseDrag"].get("result") == "PASS"
                                else "LIVE_DESKTOP_HOOK_QA_PARTIAL")
            return report
        finally:
            try:
                (output / "events.jsonl").write_text("".join(json.dumps(item, sort_keys=True) + "\n"
                    for item in live.events if item.get("type") in SAFE_TYPES))
                (output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
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
    parser.add_argument("--executable", type=Path, default=DEFAULT_APP)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "standalone-app/evidence/live-desktop-hook")
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--drag-timeout", type=float, default=60)
    parser.add_argument("--hook-timeout", type=float, default=360)
    args = parser.parse_args()
    report = run(args.executable, args.output, args.session_id, args.drag_timeout,
                 args.hook_timeout)
    print(json.dumps(report, sort_keys=True), flush=True)
    return 0 if report.get("status") == "LIVE_DESKTOP_HOOK_QA_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
