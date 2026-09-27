#!/usr/bin/env python3
"""Record the *built* standalone Electron window for v0.1.0 visual audit.

This is an observational harness. It never edits atlases, Hooks or the running
pet. The test App uses a throwaway profile and has Codex events disabled.
"""

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

from PIL import Image, ImageDraw

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.run_electron_harness import LiveHarness
from tools.run_standalone_app_qa import ROOT, command, wait_event


QA2 = ROOT / "dist/Liang no Henshin v0.1.0 QA2.app/Contents/MacOS/Electron"
ROWS = (
    ("idle", 0, 6, 1.35),
    ("running-right", 1, 8, 1.25),
    ("running-left", 2, 8, 1.25),
    ("waving", 3, 4, 0.95),
    ("jumping", 4, 5, 0.98),
    ("failed", 5, 8, 1.38),
    ("waiting", 6, 6, 1.18),
    ("running", 7, 6, 1.05),
    ("review", 8, 6, 1.18),
)


def alpha_geometry(image: Image.Image) -> dict:
    rgba = image.convert("RGBA")
    bbox = rgba.getchannel("A").getbbox()
    if bbox is None:
        return {"bbox": None, "centerX": None, "baseline": None}
    return {"bbox": bbox, "centerX": (bbox[0] + bbox[2]) / 2, "baseline": bbox[3] - 1}


def screenshot(live: LiveHarness, temporary: Path, output: Path, name: str) -> dict:
    after = command(live, type="capture", name=name)
    event = wait_event(live, lambda value: value.get("type") == "capture"
                       and value.get("name") == name, after=after, timeout=8)
    source = Path(event["file"])
    destination = output / f"{name}.png"
    shutil.copy2(source, destination)
    with Image.open(destination) as image:
        geometry = alpha_geometry(image)
        size = image.size
    recent = next((item for item in reversed(live.events[:len(live.events)])
                   if item.get("type") == "renderer" and item.get("observedAt", 0) <= event["observedAt"]), None)
    return {"file": str(destination), "observedAt": event["observedAt"], "size": size,
            "geometry": geometry, "rendered": {key: recent.get(key) for key in
            ("form", "state", "row", "frame", "visualMode", "transitionId", "transitionFrame")}
            if recent else None}


def video_gif(captures: list[dict], output: Path, *, step_ms: int = 65) -> None:
    frames = []
    for record in captures:
        with Image.open(record["file"]) as source:
            image = source.convert("RGBA")
        if image.size == (512, 512):
            image = image.resize((256, 256), Image.Resampling.NEAREST)
        frame = Image.new("RGBA", image.size, (40, 40, 40, 255))
        frame.alpha_composite(image)
        frames.append(frame.convert("RGB"))
    if not frames:
        raise ValueError("no real-window captures for recording")
    frames[0].save(output, save_all=True, append_images=frames[1:],
                   duration=step_ms, loop=0, optimize=False)


def contact_sheet(captures: list[dict], output: Path, form: str) -> dict:
    sheet = Image.new("RGBA", (8 * 192, len(ROWS) * 236), (35, 35, 35, 255))
    draw = ImageDraw.Draw(sheet)
    missing = {}
    for row_index, (name, row, count, _) in enumerate(ROWS):
        seen = {item["rendered"]["frame"]: item for item in captures
                if item["rendered"] and item["rendered"]["form"] == form
                and item["rendered"]["row"] == row and item["rendered"]["state"] == name
                and item["rendered"]["frame"] is not None}
        missing[name] = sorted(set(range(count)) - set(seen))
        for frame_index in range(count):
            x, y = frame_index * 192, row_index * 236
            draw.text((x + 3, y + 3), f"{name} {frame_index}", fill="white")
            item = seen.get(frame_index)
            if item is None:
                draw.text((x + 45, y + 105), "NOT CAPTURED", fill="#ff6666")
                continue
            with Image.open(item["file"]) as source:
                image = source.convert("RGBA")
            if image.size == (512, 512):
                image = image.resize((256, 256), Image.Resampling.NEAREST)
            sheet.alpha_composite(image.crop((32, 24, 224, 232)), (x, y + 24))
    sheet.save(output)
    return missing


def set_state(live: LiveHarness, state: str) -> int:
    command(live, type="interaction", kind="hover", value=False)
    command(live, type="interaction", kind="drag", value=None)
    command(live, type="interaction", kind="look", value=None)
    command(live, type="work", state="idle")
    after = len(live.events)
    if state in ("running-right", "running-left"):
        command(live, type="interaction", kind="drag", value=state)
    elif state == "jumping":
        command(live, type="interaction", kind="hover", value=True)
    elif state != "idle":
        command(live, type="work", state=state)
    return after


def record_form(form: str, output: Path, executable: Path, *, scale: int) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"liang-visual-{form}-") as root_string:
        root = Path(root_string)
        for name in ("home", "tmp", "user-data"):
            (root / name).mkdir()
        env = {"HOME": str(root / "home"), "TMPDIR": str(root / "tmp") + os.sep,
               "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin"),
               "LANG": "en_US.UTF-8", "LNH_STANDALONE_TEST": "1",
               "LNH_DISABLE_CODEX_EVENTS": "1", "LNH_STANDALONE_TEST_ROOT": str(root),
               "LNH_TEST_INITIAL_TIME": "2026-09-14T08:30:00+08:00" if form == "gu"
               else "2026-09-14T10:30:00+08:00"}
        process = subprocess.Popen([str(executable), f"--force-device-scale-factor={scale}"],
                                   cwd=ROOT, env=env, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, bufsize=1)
        live = LiveHarness(process)
        captures: list[dict] = []
        try:
            startup = wait_event(live, lambda item: item.get("type") == "startup", timeout=30)
            if startup.get("initialForm") != form:
                raise RuntimeError(f"expected {form}, App started {startup.get('initialForm')}")
            command(live, type="move", x=20, y=20)
            for state, row, count, duration in ROWS:
                after = set_state(live, state)
                wait_event(live, lambda item: item.get("type") == "renderer"
                           and item.get("row") == row and item.get("form") == form,
                           after=after, timeout=5)
                deadline = time.monotonic() + duration
                while time.monotonic() < deadline:
                    name = f"{form}-{scale}x-{len(captures):04d}"
                    captures.append(screenshot(live, root, output, name))
                    time.sleep(0.045)
            set_state(live, "idle")
            look = []
            for direction in range(16):
                after = command(live, type="interaction", kind="look", value=direction)
                row = 9 if direction < 8 else 10
                frame = direction % 8
                wait_event(live, lambda item: item.get("type") == "renderer"
                           and item.get("row") == row and item.get("frame") == frame,
                           after=after)
                look.append(screenshot(live, root, output, f"{form}-{scale}x-look-{direction:02d}"))
            command(live, type="interaction", kind="look", value=None)
            video_gif(captures, output / f"{form}-{scale}x-window-recording.gif")
            missing = contact_sheet(captures, output / f"{form}-{scale}x-contact-sheet.png", form)
            trace = {"build": str(executable), "form": form, "requestedScale": scale,
                     "startup": startup, "captures": captures, "lookCaptures": look,
                     "missingFrames": missing,
                     "rendererEvents": [event for event in live.events if event.get("type") in
                     ("renderer", "state", "transition-complete", "test-error", "renderer-gone")]}
            (output / f"{form}-{scale}x-trace.json").write_text(json.dumps(trace, indent=2) + "\n")
            return {"form": form, "scale": scale, "captureCount": len(captures),
                    "lookCount": len(look), "missingFrames": missing,
                    "trace": str(output / f"{form}-{scale}x-trace.json")}
        finally:
            if process.poll() is None:
                live.send(type="quit")
                process.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--executable", type=Path, default=QA2)
    parser.add_argument("--scale", type=int, choices=(1, 2), default=2)
    args = parser.parse_args()
    if not args.executable.is_file():
        parser.error("QA2 executable does not exist")
    results = [record_form(form, args.output / form, args.executable, scale=args.scale)
               for form in ("gu", "feng")]
    (args.output / f"summary-{args.scale}x.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
