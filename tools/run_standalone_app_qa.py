#!/usr/bin/env python3
"""Exercise only the project-owned standalone Electron App, never Codex."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

from PIL import Image

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.run_electron_harness import LiveHarness


ROOT = Path(__file__).resolve().parents[1]
ELECTRON = ROOT / "runtime-patch/electron-harness/node_modules/electron/dist/Electron.app/Contents/MacOS/Electron"
APP = ROOT / "standalone-app"


class StandaloneQAError(RuntimeError):
    pass


def wait_event(live: LiveHarness, predicate, *, after: int = 0, timeout: float = 15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for event in live.events[after:]:
            if predicate(event):
                return event
        if live.process.poll() is not None:
            raise StandaloneQAError(f"standalone Electron exited early: {live.process.returncode}")
        time.sleep(0.025)
    tail = [{key: event.get(key) for key in ("type", "row", "frame", "form", "normalState", "reason")}
            for event in live.events[-8:]]
    raise StandaloneQAError(f"timed out waiting for standalone App event; last={tail}; stderr={live.stderr_lines[-3:]}")


def command(live: LiveHarness, **payload):
    before = len(live.events)
    live.send(**payload)
    return before


def wait_all_frames(live: LiveHarness, row: int, count: int, *, timeout: float = 6):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        frames = {e.get("frame") for e in live.events if e.get("type") == "renderer" and e.get("row") == row}
        if frames == set(range(count)):
            return
        time.sleep(0.025)
    raise StandaloneQAError(f"row {row} renderer frames incomplete: {sorted(frames)}")


def wait_transition(live: LiveHarness, name: str, expected_form: str, count: int, *, after: int):
    complete = wait_event(live, lambda e: e.get("type") == "transition-complete"
                          and e.get("transitionId") == name, after=after, timeout=12)
    frames = sorted({e["transitionFrame"] for e in live.events[after:]
                     if e.get("type") == "renderer" and e.get("transitionId") == name
                     and isinstance(e.get("transitionFrame"), int)})
    if frames != list(range(count)) or complete.get("form") != expected_form or complete.get("underlyingState") != "review":
        raise StandaloneQAError(f"{name} renderer frames/form/work incorrect: {frames}, {complete.get('form')}, {complete.get('underlyingState')}")
    wait_event(live, lambda e: e.get("type") == "renderer"
               and e.get("form") == expected_form and e.get("visualMode") == "NORMAL", after=after)
    return frames


def capture(live: LiveHarness, name: str, output: Path):
    time.sleep(0.15)
    after = command(live, type="capture", name=name)
    event = wait_event(live, lambda e: e.get("type") == "capture" and e.get("name") == name, after=after)
    source = Path(event["file"])
    target = output / f"{name}.png"
    shutil.copy2(source, target)
    with Image.open(target) as image:
        rgba = image.convert("RGBA")
        if rgba.size[0] not in (256, 512) or rgba.size[0] != rgba.size[1] or rgba.getpixel((0, 0))[3] != 0:
            raise StandaloneQAError(f"{name} window screenshot lacks transparent margin")
        bounds = rgba.getchannel("A").getbbox()
        if bounds is None:
            after = command(live, type="inspect")
            details = wait_event(live, lambda e: e.get("type") == "inspect", after=after)
            raise StandaloneQAError(f"{name} screenshot is empty: {details}")
        if bounds[0] <= 0 or bounds[1] <= 0 or bounds[2] >= rgba.width or bounds[3] >= rgba.height:
            raise StandaloneQAError(f"{name} character reaches a window edge: {bounds}")
    return str(target)


def run_session(executable: Path, app_path: Path | None, output: Path, initial: str, *, full: bool):
    with tempfile.TemporaryDirectory(prefix="liang-standalone-qa-") as temporary:
        temporary_root = Path(temporary)
        for name in ("home", "tmp", "user-data"):
            (temporary_root / name).mkdir()
        environment = {
            "HOME": str(temporary_root / "home"),
            "TMPDIR": str(temporary_root / "tmp") + os.sep,
            "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin"),
            "LANG": "en_US.UTF-8",
            "LNH_STANDALONE_TEST": "1",
            "LNH_STANDALONE_TEST_ROOT": str(temporary_root),
            "LNH_TEST_INITIAL_TIME": initial,
        }
        launch = [str(executable)] + ([] if app_path is None else [str(app_path)])
        process = subprocess.Popen(
            launch, cwd=ROOT, env=environment,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1,
        )
        live = LiveHarness(process)
        result = {"initialTime": initial, "pid": process.pid}
        try:
            startup = wait_event(live, lambda e: e.get("type") == "startup", timeout=30)
            expected = "feng" if "10:30" in initial else "gu"
            if startup.get("initialForm") != expected or startup.get("transparent") is not True:
                raise StandaloneQAError("startup form or transparency mismatch")
            after = command(live, type="move", x=20, y=20)
            wait_event(live, lambda e: e.get("type") == "window-position", after=after)
            time.sleep(0.1)
            command(live, type="interaction", kind="hover", value=False)
            command(live, type="interaction", kind="look", value=None)
            wait_event(live, lambda e: e.get("type") == "renderer" and e.get("row") == 0
                       and e.get("form") == expected)
            result["startup"] = startup
            result["restartReconcile"] = expected
            if full:
                result["screenshots"] = {"idle": capture(live, "idle", output)}
                wait_all_frames(live, 0, 6, timeout=5)
                for state, row, count in (("running", 7, 6), ("waiting", 6, 6), ("review", 8, 6)):
                    after = command(live, type="work", state=state)
                    wait_event(live, lambda e: e.get("type") == "renderer" and e.get("row") == row
                               and e.get("frame") == count - 1, after=after, timeout=6)
                    result[state] = "RENDERER_PASS"
                after = command(live, type="interaction", kind="hover", value=True)
                wait_event(live, lambda e: e.get("type") == "renderer" and e.get("row") == 4, after=after)
                command(live, type="interaction", kind="hover", value=False)
                result["hover"] = "RENDERER_PASS"
                command(live, type="work", state="idle")
                for direction, row, frame in ((7, 9, 7), (12, 10, 4)):
                    after = command(live, type="interaction", kind="look", value=direction)
                    wait_event(live, lambda e: e.get("type") == "renderer" and e.get("row") == row
                               and e.get("frame") == frame, after=after)
                command(live, type="interaction", kind="look", value=None)
                result["lookDirections"] = "RENDERER_PASS"
                command(live, type="work", state="review")
                after = command(live, type="form", form="feng")
                wait_event(live, lambda e: e.get("type") == "renderer" and e.get("transitionId") == "gu_to_feng"
                           and e.get("transitionFrame") == 4, after=after)
                result["screenshots"]["gu_to_feng"] = capture(live, "gu_to_feng", output)
                result["guToFengFrames"] = wait_transition(live, "gu_to_feng", "feng", 10, after=after)
                after = command(live, type="form", form="gu")
                wait_event(live, lambda e: e.get("type") == "renderer" and e.get("transitionId") == "feng_to_gu"
                           and e.get("transitionFrame") == 3, after=after)
                result["screenshots"]["feng_to_gu"] = capture(live, "feng_to_gu", output)
                result["fengToGuFrames"] = wait_transition(live, "feng_to_gu", "gu", 8, after=after)
                after = command(live, type="simulate-drag")
                drag = wait_event(live, lambda e: e.get("type") == "synthetic-drag", after=after)
                result["drag"] = drag
                if drag["after"]["x"] - drag["before"]["x"] != 30 or drag["after"]["y"] != drag["before"]["y"]:
                    raise StandaloneQAError("synthetic pointer drag did not move the 256x256 window by 30 px")
                if not any(e.get("type") == "state" and e.get("normalState") == "running-right"
                           for e in live.events[after:]):
                    raise StandaloneQAError("drag did not select the running-right row")
                for at, form in (("2026-09-14T09:00:00+08:00", "feng"),
                                 ("2026-09-14T12:00:00+08:00", "gu"),
                                 ("2026-09-14T14:00:00+08:00", "feng"),
                                 ("2026-09-14T18:00:00+08:00", "gu")):
                    after = command(live, type="clock", value=at)
                    wait_event(live, lambda e: e.get("type") == "schedule" and e.get("expectedForm") == form,
                               after=after)
                    transition = "gu_to_feng" if form == "feng" else "feng_to_gu"
                    wait_transition(live, transition, form, 10 if form == "feng" else 8, after=after)
                result["scheduleE2E"] = "PASS"
            result["events"] = len(live.events)
            if not all(e.get("hitbox") == {"width": 192, "height": 208}
                       for e in live.events if e.get("type") == "renderer"):
                raise StandaloneQAError("renderer hitbox differs from 192x208")
            if any(e.get("type") in {"fatal", "renderer-gone", "renderer-load-failed", "test-error"}
                   for e in live.events):
                raise StandaloneQAError("renderer or test-control error was emitted")
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
    parser.add_argument("--executable", type=Path, default=ELECTRON)
    parser.add_argument("--app-path", type=Path, default=APP)
    parser.add_argument("--bundled", action="store_true", help="launch the packaged App without a project path argument")
    parser.add_argument("--output", type=Path, default=ROOT / "standalone-app/evidence/local-qa")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    try:
        app_path = None if args.bundled else args.app_path
        first = run_session(args.executable, app_path, args.output,
                            "2026-09-14T08:59:00+08:00", full=True)
        restart = run_session(args.executable, app_path, args.output,
                              "2026-09-14T10:30:00+08:00", full=False)
        report = {"status": "STANDALONE_APP_QA_PASS", "live": first,
                  "restart": restart, "physicalMouseGestureVerified": False}
        (args.output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(json.dumps({"status": report["status"], "report": str(args.output / "report.json")}, indent=2))
        return 0
    except (StandaloneQAError, OSError, subprocess.TimeoutExpired) as error:
        print(json.dumps({"status": "STANDALONE_APP_QA_FAILED", "reason": str(error),
                          "trace": traceback.format_exc(limit=4)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
