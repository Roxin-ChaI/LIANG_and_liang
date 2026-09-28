#!/usr/bin/env python3
"""Exercise every normal-row ordered state pair in packaged QA2 (not asset edits)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageDraw

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.audit_standalone_visual import QA2, ROWS, screenshot
from tools.run_electron_harness import LiveHarness
from tools.run_standalone_app_qa import ROOT, command, wait_event


def choose(live: LiveHarness, state: str, form: str) -> dict:
    after = len(live.events)
    command(live, type="interaction", kind="look", value=None)
    if state in ("running-right", "running-left"):
        command(live, type="interaction", kind="hover", value=False)
        command(live, type="work", state="idle")
        command(live, type="interaction", kind="drag", value=state)
    elif state == "jumping":
        command(live, type="interaction", kind="drag", value=None)
        command(live, type="work", state="idle")
        command(live, type="interaction", kind="hover", value=True)
    else:
        command(live, type="interaction", kind="drag", value=None)
        command(live, type="interaction", kind="hover", value=False)
        command(live, type="work", state=state)
    row = next(row for name, row, _, _ in ROWS if name == state)
    return wait_event(live, lambda item: item.get("type") == "renderer"
                      and item.get("form") == form and item.get("row") == row
                      and item.get("state") == state, after=after, timeout=5)


def run(form: str, output: Path, executable: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="liang-state-pairs-") as temporary:
        root = Path(temporary)
        for name in ("home", "tmp", "user-data"):
            (root / name).mkdir()
        env = {"HOME": str(root / "home"), "TMPDIR": str(root / "tmp") + os.sep,
               "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin"),
               "LANG": "en_US.UTF-8", "LNH_STANDALONE_TEST": "1",
               "LNH_DISABLE_CODEX_EVENTS": "1", "LNH_STANDALONE_TEST_ROOT": str(root),
               "LNH_TEST_INITIAL_TIME": "2026-09-14T08:30:00+08:00" if form == "gu"
               else "2026-09-14T10:30:00+08:00"}
        process = subprocess.Popen([str(executable), "--force-device-scale-factor=2"],
                                   cwd=ROOT, env=env, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, bufsize=1)
        live = LiveHarness(process)
        pairs = []
        sheet = Image.new("RGBA", (9 * 144, 9 * 180), (35, 35, 35, 255))
        draw = ImageDraw.Draw(sheet)
        try:
            startup = wait_event(live, lambda item: item.get("type") == "startup", timeout=30)
            if startup.get("initialForm") != form:
                raise RuntimeError("unexpected startup form")
            command(live, type="move", x=20, y=20)
            for source_index, (source, _, _, _) in enumerate(ROWS):
                for target_index, (target, _, _, _) in enumerate(ROWS):
                    choose(live, source, form)
                    event = choose(live, target, form)
                    item = screenshot(live, root, output, f"{form}-{source_index}-{target_index}")
                    box = item["geometry"]["bbox"]
                    pairs.append({"from": source, "to": target,
                                  "renderer": event, "capture": item,
                                  "empty": box is None,
                                  "touchesWindowEdge": bool(box and (box[0] <= 0 or box[1] <= 0
                                      or box[2] >= item["size"][0] or box[3] >= item["size"][1]))})
                    with Image.open(item["file"]) as image:
                        thumbnail = image.convert("RGBA").resize((128, 128), Image.Resampling.NEAREST)
                    x, y = target_index * 144, source_index * 180
                    sheet.alpha_composite(thumbnail, (x, y + 32))
                    draw.text((x + 2, y + 2), f"{source_index} -> {target_index}", fill="white")
            handoffs = []
            for state in ("waving", "failed", "waiting", "review"):
                choose(live, state, form)
                begin = len(live.events)
                idle = wait_event(live, lambda item: item.get("type") == "renderer"
                                  and item.get("state") == state and item.get("row") == 0,
                                  after=begin, timeout=8)
                capture = screenshot(live, root, output, f"{form}-{state}-finite-idle")
                handoffs.append({"from": state, "renderer": idle, "capture": capture})
            sheet.save(output / f"{form}-state-pairs.png")
            result = {"form": form, "pairs": pairs, "finiteHandoffs": handoffs,
                      "coverageNote": "post-paint boundary captures, not high-speed optical proof of every transient"}
            (output / f"{form}-state-pairs.json").write_text(json.dumps(result, indent=2) + "\n")
            return {"form": form, "pairCount": len(pairs),
                    "empty": sum(item["empty"] for item in pairs),
                    "edge": sum(item["touchesWindowEdge"] for item in pairs),
                    "finiteHandoffs": len(handoffs)}
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
    print(json.dumps([run(form, args.output / form, args.executable)
                      for form in ("gu", "feng")], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
