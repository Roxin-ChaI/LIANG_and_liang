#!/usr/bin/env python3
"""Probe only the existing standalone bundle's form trigger with an isolated profile."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

from run_standalone_app_qa import LiveHarness, command, wait_event


ROOT = Path(__file__).resolve().parents[1]
EXECUTABLE = ROOT / "dist/Liang no Henshin.app/Contents/MacOS/Electron"


def run() -> dict:
    if not EXECUTABLE.is_file():
        raise FileNotFoundError(EXECUTABLE)
    with tempfile.TemporaryDirectory(prefix="liang-bundle-trigger-") as temporary:
        base = Path(temporary)
        for name in ("home", "tmp", "user-data"):
            (base / name).mkdir()
        environment = {
            "HOME": str(base / "home"),
            "TMPDIR": str(base / "tmp") + os.sep,
            "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin"),
            "LANG": "en_US.UTF-8",
            "LNH_STANDALONE_TEST": "1",
            "LNH_DISABLE_CODEX_EVENTS": "1",
            "LNH_STANDALONE_TEST_ROOT": str(base),
            "LNH_TEST_INITIAL_TIME": "2026-09-14T08:59:00+08:00",
        }
        process = subprocess.Popen([str(EXECUTABLE)], cwd=ROOT, env=environment,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, bufsize=1)
        live = LiveHarness(process)
        result: dict = {"bundle": str(EXECUTABLE.relative_to(ROOT)), "pid": process.pid}
        try:
            startup = wait_event(live, lambda event: event.get("type") == "startup", timeout=30)
            result["initialForm"] = startup.get("initialForm")
            for target, transition, expected in (("feng", "gu_to_feng", 10),
                                                  ("gu", "feng_to_gu", 8)):
                after = command(live, type="form", form=target)
                completion = wait_event(live,
                    lambda event: event.get("type") == "transition-complete"
                    and event.get("transitionId") == transition,
                    after=after, timeout=12)
                wait_event(live,
                    lambda event: event.get("type") == "renderer"
                    and event.get("form") == target and event.get("visualMode") == "NORMAL",
                    after=after, timeout=5)
                seen = sorted({event.get("transitionFrame") for event in live.events[after:]
                    if event.get("type") == "renderer" and event.get("transitionId") == transition
                    and isinstance(event.get("transitionFrame"), int)})
                result[transition] = {"triggered": True, "completedForm": completion.get("form"),
                                      "expectedFrames": expected, "rendererFramesSeen": seen,
                                      "allFramesSeen": seen == list(range(expected))}
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
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
