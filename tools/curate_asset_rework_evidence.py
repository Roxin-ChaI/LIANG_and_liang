"""Preserve full oversized actual-window frames and explicit old-art comparisons."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.curate_transition_evidence import curate
from tools.audit_standalone_state_races import curate_race_evidence

ROOT = Path(__file__).resolve().parents[1]
PRIOR = ROOT / "docs/visual-rework/v0.1.0/final/transitions"


def sheet(items: list[tuple[str, Path]], output: Path, columns: int) -> None:
    """Nearest-only QA thumbnailing, not animation resampling or subject cropping."""
    rows = (len(items) + columns - 1) // columns
    canvas = Image.new("RGBA", (columns * 256, rows * 284), (35, 35, 35, 255))
    draw = ImageDraw.Draw(canvas)
    for index, (label, file) in enumerate(items):
        x, y = (index % columns) * 256, (index // columns) * 284
        draw.text((x + 4, y + 4), label, fill="white")
        with Image.open(file) as original:
            image = original.convert("RGBA")
        if image.size == (512, 512):
            image = image.resize((256, 256), Image.Resampling.NEAREST)
        if image.size != (256, 256):
            raise ValueError("unexpected actual-window capture dimensions")
        canvas.alpha_composite(image, (x, y + 28))
    canvas.save(output)


def preserve(raw: Path, output: Path) -> dict:
    summary = curate(raw, output)
    trace = json.loads((raw / "transition-trace.json").read_text())
    frames_dir = output / "frames"
    frames_dir.mkdir(exist_ok=True)
    for scenario in trace["scenarios"]:
        label = scenario["label"]
        items = [("before", Path(scenario["before"]["file"]))]
        for frame in scenario["frames"]:
            file = Path(frame["file"])
            shutil.copy2(file, frames_dir / file.name)
            items.append((f"frame {frame['frameIndex']}", file))
        items.append(("after", Path(scenario["after"]["file"])))
        sheet(items, output / f"{label}-full-window-sheet.png", 6)
        if scenario["mode"] in ("idle", "running"):
            count = scenario["frameCount"]
            suffixes = ("before", "00", f"{count - 1:02d}", "after")
            comparisons = [(f"{row}: {suffix}", directory / f"{label}-{suffix}.png")
                           for row, directory in (("prior", PRIOR), ("fixed player; same art", output))
                           for suffix in suffixes]
            sheet(comparisons, output / f"{label}-prior-vs-fixed-player.png", 4)
    summary["artwork"] = "UNCHANGED_FROZEN_TRANSITIONS; NOT_NEW_ASSET_INTEGRATION"
    summary["allIntermediateWindowFramesPreserved"] = True
    (output / "transition-timeline.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--race", type=Path, action="append", default=[])
    parser.add_argument("--ungated", type=Path)
    args = parser.parse_args()
    value = preserve(args.raw, args.output)
    for index, raw in enumerate(args.race, 1):
        destination = args.output.parent / f"race-{index}"
        curate_race_evidence(raw, destination)
        if index == 1:
            sheet([("prior: frame4 stalled", ROOT / "docs/visual-rework/v0.1.0/final/races/stalled-after-competing-states.png"),
                   ("fixed: completed; Review", destination / "after-competing-states.png")],
                  args.output.parent / "frame4-prior-vs-fixed-player.png", 2)
    if args.ungated:
        trace = json.loads((args.ungated / "ungated-trace.json").read_text())
        destination = args.output.parent / "ungated"
        destination.mkdir(exist_ok=True)
        for scenario in trace["scenarios"]:
            shutil.copy2(args.ungated / scenario["gif"], destination / scenario["gif"])
        trace["events"] = [e for e in trace["events"] if e.get("type") in (
            "state", "renderer", "transition-dwell-start", "transition-dwell-end",
            "transition-complete", "renderer-error", "renderer-gone", "test-error")]
        (destination / "ungated-timeline.json").write_text(json.dumps(trace, indent=2) + "\n")
    print(json.dumps({"scenarios": len(value["scenarios"]), "output": str(args.output)}))
