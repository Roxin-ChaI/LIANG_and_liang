#!/usr/bin/env python3
"""Curate real-window candidate evidence while preserving the original audit."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.compile_standalone_visual_evidence import selected, alpha_metrics, look_sheet


def collect(raw: Path, output: Path, pairs: Path | None = None) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    result = {"captureKind": "actual isolated candidate Electron window; capturePage sequence, not OS video",
              "forms": {}}
    for form in ("gu", "feng"):
        trace = json.loads((raw / form / f"{form}-2x-trace.json").read_text())
        frames = selected(trace, form)
        rows = {name: alpha_metrics(items, 2) for name, items in frames.items()}
        for suffix in ("contact-sheet.png", "window-recording.gif"):
            shutil.copy2(raw / form / f"{form}-2x-{suffix}", output / f"{form}-{suffix}")
        look_sheet(trace["lookCaptures"], output / f"{form}-look-directions.png")
        result["forms"][form] = {"rows": rows, "missingFrames": trace["missingFrames"],
                                 "build": trace["build"], "lookCount": len(trace["lookCaptures"])}
        if pairs and (pairs / form / f"{form}-state-pairs.json").is_file():
            report = json.loads((pairs / form / f"{form}-state-pairs.json").read_text())
            shutil.copy2(pairs / form / f"{form}-state-pairs.png", output / f"{form}-state-pairs.png")
            result["forms"][form]["statePairs"] = [
                {"from": item["from"], "to": item["to"], "geometry": item["capture"]["geometry"],
                 "empty": item["empty"], "touchesWindowEdge": item["touchesWindowEdge"]}
                for item in report["pairs"]]
    gu = result["forms"]["gu"]["rows"]
    canonical = gu["idle"]["baselinesCssPx"][0]
    grounded = ("waving", "failed", "waiting", "running", "review")
    result["guWorkBaselinePass"] = all(set(gu[state]["baselinesCssPx"]) == {canonical} for state in grounded)
    (output / "window-metrics.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--pairs", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = collect(args.raw, args.output, args.pairs)
    print(json.dumps({"output": str(args.output), "guWorkBaselinePass": result["guWorkBaselinePass"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
