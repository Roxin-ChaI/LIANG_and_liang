"""Ungated actual Electron-window sampling; no frame hold or playback edits."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.audit_standalone_transitions import copy_capture, stage
from tools.run_electron_harness import LiveHarness
from tools.run_standalone_app_qa import ROOT, command, wait_event


def observed_gif_durations(timestamps: list[int]) -> list[int]:
    """GIF uses 10 ms units. Source timing remains exact in the JSON sidecar."""
    if len(timestamps) < 2 or any(b <= a for a, b in zip(timestamps, timestamps[1:])):
        raise ValueError("strictly increasing capture timestamps required")
    return [max(10, 10 * round((b - a) / 10)) for a, b in zip(timestamps, timestamps[1:])] + [100]


def recording(captures: list[dict], output: Path) -> None:
    frames = []
    for capture in captures:
        with Image.open(capture["file"]) as source:
            image = source.convert("RGBA")
        if image.size == (512, 512):
            image = image.resize((256, 256), Image.Resampling.NEAREST)
        frame = Image.new("RGBA", image.size, (35, 35, 35, 255))
        frame.alpha_composite(image)
        frames.append(frame.convert("RGB"))
    frames[0].save(output, save_all=True, append_images=frames[1:],
                   duration=observed_gif_durations([c["observedAt"] for c in captures]),
                   loop=0, optimize=False)


def record(executable: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="liang-ungated-video-") as temporary:
        root = Path(temporary)
        for name in ("home", "tmp", "user-data"):
            (root / name).mkdir()
        env = {"HOME": str(root / "home"), "TMPDIR": str(root / "tmp") + os.sep,
               "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin"), "LANG": "en_US.UTF-8",
               "LNH_STANDALONE_TEST": "1", "LNH_DISABLE_CODEX_EVENTS": "1",
               "LNH_STANDALONE_TEST_ROOT": str(root),
               "LNH_TEST_INITIAL_TIME": "2026-09-14T08:30:00+08:00"}
        process = subprocess.Popen([str(executable), "--force-device-scale-factor=2"],
                                   cwd=ROOT, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, bufsize=1)
        live = LiveHarness(process)
        try:
            wait_event(live, lambda e: e.get("type") == "startup", timeout=30)
            command(live, type="move", x=20, y=20)
            scenarios = []
            for mode in ("idle", "running"):
                for source in ("gu", "feng"):
                    target = "feng" if source == "gu" else "gu"
                    label = f"{mode}-{source}_to_{target}"
                    stage(live, mode, source)
                    captures = [copy_capture(live, output, f"{label}-sample-000")]
                    after = command(live, type="form", form=target)
                    deadline = time.monotonic() + 10
                    while not any(e.get("type") == "transition-complete" for e in live.events[after:]):
                        if time.monotonic() > deadline:
                            raise RuntimeError("ungated transition stalled")
                        captures.append(copy_capture(live, output, f"{label}-sample-{len(captures):03d}"))
                        time.sleep(0.02)
                    complete = wait_event(live, lambda e: e.get("type") == "transition-complete", after=after)
                    wait_event(live, lambda e: e.get("type") == "renderer" and e.get("form") == target
                               and e.get("visualMode") == "NORMAL", after=after)
                    captures.append(copy_capture(live, output, f"{label}-sample-{len(captures):03d}"))
                    recording(captures, output / f"{label}-ungated-window.gif")
                    scenarios.append({"label": label, "completion": complete,
                                      "captureTimestamps": [c["observedAt"] for c in captures],
                                      "gif": f"{label}-ungated-window.gif"})
            result = {"captureKind": "UNGATED_ACTUAL_WINDOW_SAMPLING_NOT_OS_SCREEN_RECORDING",
                      "timing": "observed capture intervals rounded to GIF 10 ms units; no frame gate",
                      "limitations": "capturePage adds load; sampling may miss a display frame; GIF quantizes colors",
                      "build": str(executable), "scenarios": scenarios, "events": live.events}
            (output / "ungated-trace.json").write_text(json.dumps(result, indent=2) + "\n")
            return result
        finally:
            if process.poll() is None:
                live.send(type="quit")
                process.wait(timeout=5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = record(args.executable, args.output)
    print(json.dumps({"scenarios": len(result["scenarios"]), "output": str(args.output)}))
