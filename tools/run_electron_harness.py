#!/usr/bin/env python3
"""Run the project-owned Electron harness with a throwaway test Bundle ID.

This never launches or copies Codex. It signs only a temporary copy of the
public Electron binary and uses no production Keychain group or login token.
"""

from __future__ import annotations

import argparse
import json
import os
import plistlib
import queue
import shutil
import subprocess
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

from PIL import Image, ImageChops

if __package__:
    from .pet_runtime_client import set_target_form
    from .time_form_scheduler import FormScheduler
else:
    from pet_runtime_client import set_target_form
    from time_form_scheduler import FormScheduler

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "runtime-patch/electron-harness"
ELECTRON_APP = HARNESS / "node_modules/electron/dist/Electron.app"
TEST_BUNDLE_ID = "com.liang-no-henshin.runtime-harness"
EXPECTED_ATLAS = {
    "gu_to_feng": 10,
    "feng_to_gu": 8,
}


class HarnessError(RuntimeError):
    pass


def command(*args: str) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(args, capture_output=True, check=False)
    if result.returncode:
        raise HarnessError(f"command failed: {args[0]} ({result.returncode})")
    return result


def prepare_app(root: Path) -> Path:
    if not ELECTRON_APP.is_dir():
        raise HarnessError("independent Electron binary is missing")
    app = root / "LiangHarness.app"
    command("ditto", str(ELECTRON_APP), str(app))
    info_path = app / "Contents/Info.plist"
    with info_path.open("rb") as handle:
        info = plistlib.load(handle)
    info["CFBundleIdentifier"] = TEST_BUNDLE_ID
    info["CFBundleName"] = "Liang Runtime Harness"
    with info_path.open("wb") as handle:
        plistlib.dump(info, handle)
    entitlements = root / "test-entitlements.plist"
    with entitlements.open("wb") as handle:
        plistlib.dump(
            {
                "com.apple.security.cs.allow-jit": True,
                "com.apple.security.cs.allow-unsigned-executable-memory": True,
                "com.apple.security.cs.disable-library-validation": True,
            },
            handle,
        )
    command(
        "codesign", "--force", "--deep", "--sign", "-", "--options", "runtime",
        "--entitlements", str(entitlements), str(app),
    )
    command("codesign", "--verify", "--deep", "--strict", str(app))
    detail = command("codesign", "-dv", "--verbose=4", str(app))
    text = (detail.stdout + detail.stderr).decode("utf-8", "replace")
    if f"Identifier={TEST_BUNDLE_ID}" not in text.splitlines():
        raise HarnessError("temporary App Bundle ID did not change")
    if "TeamIdentifier=2DC432GLL2" in text:
        raise HarnessError("temporary App retains production team identity")
    entitlement_result = command("codesign", "-d", "--entitlements", "-", "--xml", str(app))
    actual = plistlib.loads(entitlement_result.stdout)
    if "keychain-access-groups" in actual:
        raise HarnessError("temporary App unexpectedly has Keychain groups")
    return app


def isolated_environment(root: Path) -> dict[str, str]:
    """Pass only test paths and non-secret process settings to Electron."""
    return {
        "HOME": str(root / "home"),
        "CODEX_HOME": str(root / "codex-home"),
        "TMPDIR": str(root / "tmp") + os.sep,
        "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin"),
        "LANG": "en_US.UTF-8",
        "LNH_HARNESS_ROOT": str(root),
        "LNH_HARNESS_BUNDLE_ID": TEST_BUNDLE_ID,
    }


class LiveHarness:
    def __init__(self, process: subprocess.Popen[str]) -> None:
        self.process = process
        self.events: list[dict[str, object]] = []
        self.inbox: queue.Queue[dict[str, object]] = queue.Queue()
        self.stderr_lines: list[str] = []
        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()

    def _read_stdout(self) -> None:
        assert self.process.stdout is not None
        for line in self.process.stdout:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict):
                self.events.append(event)
                self.inbox.put(event)

    def _read_stderr(self) -> None:
        assert self.process.stderr is not None
        for line in self.process.stderr:
            if len(self.stderr_lines) < 200:
                self.stderr_lines.append(line.rstrip())

    def wait(self, predicate: Callable[[dict[str, object]], bool], timeout: float = 20) -> dict[str, object]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise HarnessError(f"Electron exited early ({self.process.returncode})")
            try:
                event = self.inbox.get(timeout=min(0.25, max(0.01, deadline - time.monotonic())))
            except queue.Empty:
                continue
            if predicate(event):
                return event
        raise HarnessError("timed out waiting for Electron event")

    def send(self, **command_data: object) -> None:
        if self.process.stdin is None:
            raise HarnessError("Electron control stdin unavailable")
        self.process.stdin.write(json.dumps(command_data) + "\n")
        self.process.stdin.flush()


def wait_transition(
    live: LiveHarness, name: str, target: str, *, since: int = 0, timeout: float = 15
) -> list[int]:
    live.wait(lambda e: e.get("type") == "completed" and e.get("transitionId") == name, timeout)
    frames = [
        int(event["frameIndex"])
        for event in live.events[since:]
        if event.get("type") == "renderer" and event.get("transitionId") == name
        and isinstance(event.get("frameIndex"), int)
    ]
    unique = sorted(set(frames))
    if unique != list(range(EXPECTED_ATLAS[name])):
        raise HarnessError(f"renderer did not show every {name} frame: {unique}")
    if live.events[-1].get("currentForm") != target:
        # Renderer delivery can trail the completion event; observe it directly.
        live.wait(lambda e: e.get("type") == "renderer" and e.get("mode") == "NORMAL"
                  and e.get("currentForm") == target)
    return unique


def validate_visual(events: list[dict[str, object]], evidence: Path) -> dict[str, object]:
    geometry = {}
    for name, dimensions, offsets in [
        ("gu_to_feng", (224, 240), (-16, -18)),
        ("feng_to_gu", (208, 224), (-9, -14)),
    ]:
        matched = [event for event in events if event.get("type") == "renderer"
                   and event.get("transitionId") == name]
        if not matched:
            raise HarnessError(f"no renderer geometry for {name}")
        for event in matched:
            normal, overlay = event["normal"], event["overlay"]
            if normal != {"x": 96, "y": 42, "width": 192, "height": 208}:
                raise HarnessError(f"normal drag hitbox changed during {name}")
            if (overlay["width"], overlay["height"]) != dimensions:
                raise HarnessError(f"incorrect overlay dimensions for {name}")
            if (overlay["x"], overlay["y"]) != (96 + offsets[0], 42 + offsets[1]):
                raise HarnessError(f"overlay anchor changed for {name}")
            if event["overlayPointerEvents"] != "none" or event["normalPointerEvents"] != "auto":
                raise HarnessError(f"overlay captured the drag hitbox for {name}")
            if (event["overlayNaturalWidth"], event["overlayNaturalHeight"]) != dimensions:
                raise HarnessError(f"actual decoded frame dimensions changed for {name}")
        geometry[name] = {"size": dimensions, "anchor": offsets, "samples": len(matched)}
    edge = next((event for event in events if event.get("type") == "edge"), None)
    if edge is None:
        raise HarnessError("window-edge move was not observed")
    bounds, area = edge["bounds"], edge["workArea"]
    if bounds["x"] + bounds["width"] != area["x"] + area["width"]:
        raise HarnessError("test window did not reach work-area right edge")
    if bounds["y"] + bounds["height"] != area["y"] + area["height"]:
        raise HarnessError("test window did not reach work-area bottom edge")
    screenshots = {}
    for name in ("idle", "gu_to_feng_edge", "feng_to_gu"):
        file = evidence / f"{name}.png"
        with Image.open(file) as image:
            rgb = image.convert("RGB")
            width, height = rgb.size
            upper = rgb.crop((0, 0, width, int(height * 0.85)))
            background = Image.new("RGB", upper.size, rgb.getpixel((0, 0)))
            bounds = ImageChops.difference(upper, background).getbbox()
            if bounds is None or bounds[0] < 8 or bounds[1] < 8 or bounds[2] > width - 8:
                raise HarnessError(f"blank or clipped renderer screenshot: {name}")
            screenshots[name] = {"pixels": [width, height], "contentBounds": list(bounds)}
    return {"geometry": geometry, "screenshots": screenshots,
            "physicalScreenCompositorVerified": False}


def drive(root: Path, app: Path, *, smoke: bool) -> dict[str, object]:
    for subdir in ["home", "codex-home", "tmp"]:
        (root / subdir).mkdir(mode=0o700)
    environment = isolated_environment(root)
    executable = app / "Contents/MacOS/Electron"
    process = subprocess.Popen(
        [str(executable), str(HARNESS)], env=environment,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, bufsize=1,
    )
    live = LiveHarness(process)
    socket = root / "socket/runtime.sock"
    report: dict[str, object] = {"status": "BLOCKED", "pid": process.pid, "smoke": smoke}
    try:
        startup = live.wait(lambda e: e.get("type") == "startup", 30)
        if startup.get("bundleId") != TEST_BUNDLE_ID or startup.get("socketMode") != 0o600:
            raise HarnessError("startup identity/socket invariant failed")
        live.wait(lambda e: e.get("type") == "renderer" and e.get("mode") == "NORMAL", 15)
        live.send(type="capture", name="idle")
        live.wait(lambda e: e.get("type") == "capture" and e.get("name") == "idle")
        if smoke:
            report["status"] = "PROJECT_ELECTRON_HARNESS_SMOKE_PASS"
            return report

        since = len(live.events)
        response = set_target_form("feng", socket_path=socket, request_id="g2f", animate=True)
        if not response.get("accepted"):
            raise HarnessError("Gu to Feng bridge request rejected")
        live.wait(lambda e: e.get("type") == "renderer" and e.get("transitionId") == "gu_to_feng"
                  and e.get("frameIndex") == 4)
        live.send(type="edge")
        live.wait(lambda e: e.get("type") == "edge")
        live.send(type="capture", name="gu_to_feng_edge")
        live.wait(lambda e: e.get("type") == "capture" and e.get("name") == "gu_to_feng_edge")
        g2f = wait_transition(live, "gu_to_feng", "feng", since=since)

        since = len(live.events)
        response = set_target_form("gu", socket_path=socket, request_id="f2g", animate=True)
        if not response.get("accepted"):
            raise HarnessError("Feng to Gu bridge request rejected")
        live.wait(lambda e: e.get("type") == "renderer" and e.get("transitionId") == "feng_to_gu"
                  and e.get("frameIndex") == 3)
        live.send(type="capture", name="feng_to_gu")
        live.wait(lambda e: e.get("type") == "capture" and e.get("name") == "feng_to_gu")
        f2g = wait_transition(live, "feng_to_gu", "gu", since=since)

        before = len([event for event in live.events if event.get("type") == "state"])
        response = set_target_form("gu", socket_path=socket, request_id="duplicate", animate=True)
        if response.get("transitioning"):
            raise HarnessError("duplicate target restarted transition")
        live.wait(lambda e: e.get("type") == "bridge" and e.get("requestId") == "duplicate")

        set_target_form("feng", socket_path=socket, request_id="reverse-start", animate=True)
        started = live.wait(lambda e: e.get("type") == "renderer" and e.get("transitionId") == "gu_to_feng"
                            and e.get("frameIndex") == 2)
        old_token = started["operationToken"]
        set_target_form("gu", socket_path=socket, request_id="reverse-stop", animate=True)
        live.wait(lambda e: e.get("type") == "renderer" and e.get("mode") == "NORMAL"
                  and e.get("currentForm") == "gu")
        live.send(type="stale-complete", operationToken=old_token)
        stale = live.wait(lambda e: e.get("type") == "stale-complete")
        if stale.get("completed") or not stale.get("stale"):
            raise HarnessError("stale operation committed after cancellation")

        since = len(live.events)
        set_target_form("feng", socket_path=socket, request_id="priority-start", animate=True)
        live.wait(lambda e: e.get("type") == "renderer" and e.get("transitionId") == "gu_to_feng"
                  and e.get("frameIndex") == 1)
        live.send(type="interaction", kind="hover", value=True)
        live.send(type="interaction", kind="drag", value="running-right")
        live.send(type="underlying", value="failed")
        priority = live.wait(lambda e: e.get("type") == "state" and e.get("reason") == "underlying")
        if priority.get("mode") != "TRANSITIONING":
            raise HarnessError("interaction preempted transition")
        wait_transition(live, "gu_to_feng", "feng", since=since)

        live.send(type="reset", initialForm="gu", reducedMotion=True)
        live.wait(lambda e: e.get("type") == "state" and e.get("reason") == "reset")
        response = set_target_form("feng", socket_path=socket, request_id="reduced-motion", animate=True)
        if response.get("transitioning"):
            raise HarnessError("reduced motion did not commit immediately")
        live.wait(lambda e: e.get("type") == "renderer" and e.get("mode") == "NORMAL"
                  and e.get("currentForm") == "feng")

        live.send(type="reset", initialForm="gu", reducedMotion=False)
        live.wait(lambda e: e.get("type") == "state" and e.get("reason") == "reset")
        scheduler = FormScheduler()
        schedule_events = []
        for timestamp in [
            "2026-09-21T08:59:00+08:00", "2026-09-21T09:00:00+08:00",
            "2026-09-21T12:00:00+08:00", "2026-09-21T14:00:00+08:00",
            "2026-09-21T18:00:00+08:00",
        ]:
            decision = scheduler.decide(datetime.fromisoformat(timestamp))
            animate = scheduler.last_acknowledged_form is not None
            if decision.should_send:
                request_id = f"scheduler-{timestamp[11:16]}"
                since = len(live.events)
                result = set_target_form(decision.expected_form, socket_path=socket,
                                         request_id=request_id, animate=animate)
                scheduler.record_delivery(decision.expected_form, result)
                if result.get("transitioning"):
                    name = "gu_to_feng" if decision.expected_form == "feng" else "feng_to_gu"
                    wait_transition(live, name, decision.expected_form, since=since)
                else:
                    live.wait(lambda e: e.get("type") == "renderer" and e.get("mode") == "NORMAL"
                              and e.get("currentForm") == decision.expected_form)
                schedule_events.append({"time": timestamp, "form": decision.expected_form,
                                        "animate": animate, "bridgeAccepted": result.get("accepted")})
        report.update({
            "status": "PROJECT_ELECTRON_HARNESS_PASS",
            "guToFengFrames": g2f,
            "fengToGuFrames": f2g,
            "duplicateNoTransition": True,
            "reverseStaleCompletionIgnored": True,
            "priorityPreserved": True,
            "reducedMotionImmediate": True,
            "scheduler": schedule_events,
            "stateEventsBeforeDuplicate": before,
            "visualChecks": validate_visual(live.events, root / "evidence"),
        })
        return report
    except Exception as error:
        report["status"] = "PROJECT_ELECTRON_HARNESS_BLOCKED"
        report["reason"] = str(error)
        return report
    finally:
        if process.poll() is None:
            try:
                live.send(type="quit")
                live.wait(lambda e: e.get("type") == "quit", 5)
            except (HarnessError, BrokenPipeError):
                pass
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        report["exitCode"] = process.returncode
        report["socketRemoved"] = not socket.exists()
        report["rendererEventCount"] = sum(event.get("type") == "renderer" for event in live.events)
        report["runtimeExceptions"] = [event for event in live.events if event.get("type") in {"fatal", "renderer-gone", "renderer-load-failed", "control-error"}]
        report["stderrTail"] = live.stderr_lines[-20:]
        if report["runtimeExceptions"]:
            report["status"] = "PROJECT_ELECTRON_HARNESS_BLOCKED"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    output = HARNESS / "evidence" / ("phase8c-smoke" if args.smoke else "phase8c")
    report: dict[str, object] = {"status": "BLOCKED"}
    with tempfile.TemporaryDirectory(prefix="liang-electron-harness-", dir="/private/tmp") as temporary:
        root = Path(temporary).resolve()
        try:
            app = prepare_app(root)
            report = drive(root, app, smoke=args.smoke)
        except (HarnessError, OSError, ValueError) as error:
            report = {"status": "PROJECT_ELECTRON_HARNESS_BLOCKED", "reason": str(error)}
        finally:
            source = root / "evidence"
            output.mkdir(parents=True, exist_ok=True)
            if source.is_dir():
                for file in source.iterdir():
                    if file.is_file() and file.suffix in {".jsonl", ".png"}:
                        shutil.copy2(file, output / file.name)
            (output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("status") in {"PROJECT_ELECTRON_HARNESS_PASS", "PROJECT_ELECTRON_HARNESS_SMOKE_PASS"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
