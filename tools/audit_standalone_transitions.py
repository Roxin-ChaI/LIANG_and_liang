#!/usr/bin/env python3
"""Capture both one-shot transformations in the actual isolated QA2 window."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.audit_standalone_visual import QA2, alpha_geometry, video_gif
from tools.run_electron_harness import LiveHarness
from tools.run_standalone_app_qa import ROOT, command, wait_event

COUNTS = {"gu_to_feng": 10, "feng_to_gu": 8}
MODES = ("idle", "running", "hover")


def copy_capture(live: LiveHarness, output: Path, name: str) -> dict:
    after = command(live, type="capture", name=name)
    event = wait_event(live, lambda item: item.get("type") == "capture"
                       and item.get("name") == name, after=after, timeout=8)
    destination = output / f"{name}.png"
    shutil.copy2(event["file"], destination)
    with Image.open(destination) as image:
        geometry = alpha_geometry(image)
    return {"file": str(destination), "observedAt": event["observedAt"], "geometry": geometry}


def transition_sheet(captures: list[dict], before: dict, after: dict, output: Path, label: str) -> None:
    items = [("before", before), *((str(i), item) for i, item in enumerate(captures)), ("after", after)]
    sheet = Image.new("RGBA", (len(items) * 192, 236), (35, 35, 35, 255))
    draw = ImageDraw.Draw(sheet)
    for index, (frame, item) in enumerate(items):
        x = index * 192
        draw.text((x + 3, 3), f"{label} {frame}", fill="white")
        with Image.open(item["file"]) as source:
            image = source.convert("RGBA")
        if image.size == (512, 512):
            image = image.resize((256, 256), Image.Resampling.NEAREST)
        sheet.alpha_composite(image.crop((32, 24, 224, 232)), (x, 24))
    sheet.save(output)


def changed_pixel_count(first: Path, second: Path) -> int:
    with Image.open(first) as a, Image.open(second) as b:
        difference = ImageChops.difference(a.convert("RGBA"), b.convert("RGBA"))
        if a.size != b.size:
            raise ValueError("transition screenshot sizes differ")
        return sum(any(channel for channel in pixel) for pixel in difference.get_flattened_data())


def stage(live: LiveHarness, mode: str, form: str) -> None:
    command(live, type="interaction", kind="hover", value=False)
    command(live, type="interaction", kind="drag", value=None)
    command(live, type="interaction", kind="look", value=None)
    command(live, type="work", state="running" if mode == "running" else "idle")
    if mode == "hover":
        after = command(live, type="interaction", kind="hover", value=True)
        row = 4
    else:
        after = len(live.events)
        row = 7 if mode == "running" else 0
    wait_event(live, lambda item: item.get("type") == "renderer"
               and item.get("form") == form and item.get("row") == row, after=after)


def record_transition(live: LiveHarness, output: Path, source: str, mode: str) -> dict:
    target = "feng" if source == "gu" else "gu"
    transition_id = f"{source}_to_{target}"
    label = f"{mode}-{transition_id}"
    count = COUNTS[transition_id]
    stage(live, mode, source)
    before = copy_capture(live, output, f"{label}-before")
    command(live, type="frame-capture", value=True)
    after_index = command(live, type="form", form=target)
    frames = []
    for index in range(count):
        event = wait_event(live, lambda item: item.get("type") == "frame-capture"
                           and item.get("transitionId") == transition_id
                           and item.get("frameIndex") == index, after=after_index, timeout=10)
        destination = output / f"{label}-{index:02d}.png"
        shutil.copy2(event["file"], destination)
        with Image.open(destination) as image:
            geometry = alpha_geometry(image)
        frames.append({"file": str(destination), "observedAt": event["observedAt"],
                       "frameIndex": index, "geometry": geometry})
    complete = wait_event(live, lambda item: item.get("type") == "transition-complete"
                          and item.get("transitionId") == transition_id, after=after_index, timeout=10)
    wait_event(live, lambda item: item.get("type") == "renderer"
               and item.get("form") == target and item.get("visualMode") == "NORMAL",
               after=after_index, timeout=5)
    after = copy_capture(live, output, f"{label}-after")
    transition_sheet(frames, before, after, output / f"{label}-sheet.png", label)
    video_gif([before, *frames, after], output / f"{label}-window-recording.gif", step_ms=140)
    timing = [frames[index + 1]["observedAt"] - frames[index]["observedAt"]
              for index in range(count - 1)]
    return {"label": label, "source": source, "target": target, "mode": mode,
            "frameCount": len(frames), "observedIntervalsMs": timing,
            "beforeToFirstChangedPixels": changed_pixel_count(Path(before["file"]), Path(frames[0]["file"])),
            "lastToAfterChangedPixels": changed_pixel_count(Path(frames[-1]["file"]), Path(after["file"])),
            "lastFrameToCompletionMs": complete["observedAt"] - frames[-1]["observedAt"],
            "complete": complete, "before": before, "frames": frames, "after": after}


def record_session(output: Path, executable: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="liang-transition-visual-") as temporary:
        root = Path(temporary)
        for name in ("home", "tmp", "user-data"):
            (root / name).mkdir()
        env = {"HOME": str(root / "home"), "TMPDIR": str(root / "tmp") + os.sep,
               "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin"),
               "LANG": "en_US.UTF-8", "LNH_STANDALONE_TEST": "1",
               "LNH_DISABLE_CODEX_EVENTS": "1", "LNH_STANDALONE_TEST_ROOT": str(root),
               "LNH_TEST_INITIAL_TIME": "2026-09-14T08:30:00+08:00"}
        process = subprocess.Popen([str(executable), "--force-device-scale-factor=2"],
                                   cwd=ROOT, env=env, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, bufsize=1)
        live = LiveHarness(process)
        try:
            startup = wait_event(live, lambda item: item.get("type") == "startup", timeout=30)
            if startup.get("initialForm") != "gu":
                raise RuntimeError("isolated QA2 did not start as Gu")
            command(live, type="move", x=20, y=20)
            scenarios = []
            for mode in MODES:
                for source in ("gu", "feng"):
                    scenarios.append(record_transition(live, output, source, mode))
            # The screenshot gate deliberately lengthens each frame. Measure
            # a separate ungated pass before making any playback-duration claim.
            command(live, type="frame-capture", value=False)
            command(live, type="interaction", kind="hover", value=False)
            command(live, type="work", state="idle")
            ungated = []
            for source in ("gu", "feng"):
                target = "feng" if source == "gu" else "gu"
                transition_id = f"{source}_to_{target}"
                after_index = command(live, type="form", form=target)
                complete = wait_event(live, lambda item: item.get("type") == "transition-complete"
                                      and item.get("transitionId") == transition_id,
                                      after=after_index, timeout=10)
                timestamps = {}
                for event in live.events[after_index:]:
                    if event.get("type") == "renderer" and event.get("transitionId") == transition_id:
                        index = event.get("transitionFrame")
                        if isinstance(index, int) and index not in timestamps:
                            timestamps[index] = event["observedAt"]
                ungated.append({"transitionId": transition_id, "frameTimestamps": timestamps,
                                "observedIntervalsMs": [timestamps[i + 1] - timestamps[i]
                                                        for i in range(COUNTS[transition_id] - 1)
                                                        if i in timestamps and i + 1 in timestamps],
                                "lastFrameToCompletionMs": complete["observedAt"]
                                - timestamps[max(timestamps)]})
            events = [item for item in live.events if item.get("type") in
                      ("state", "renderer", "transition-complete", "frame-capture-error", "test-error")]
            report = {"captureKind": "QA2 Electron webContents.capturePage with deterministic frame gate",
                      "build": str(executable), "startup": startup,
                      "scenarios": scenarios, "ungatedTimings": ungated, "events": events}
            (output / "transition-trace.json").write_text(json.dumps(report, indent=2) + "\n")
            return {"scenarios": [item["label"] for item in scenarios],
                    "output": str(output / "transition-trace.json")}
        finally:
            if process.poll() is None:
                live.send(type="quit")
                process.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--executable", type=Path, default=QA2)
    args = parser.parse_args()
    if not args.executable.is_file():
        parser.error("QA2 executable missing")
    result = record_session(args.output, args.executable)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
