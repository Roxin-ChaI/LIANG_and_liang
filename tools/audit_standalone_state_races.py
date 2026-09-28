#!/usr/bin/env python3
"""Observe scheduler/animation races in an isolated packaged candidate."""

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

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.audit_standalone_visual import QA2, screenshot, video_gif
from tools.run_electron_harness import LiveHarness
from tools.run_standalone_app_qa import ROOT, StandaloneQAError, command, wait_event


def capture(live: LiveHarness, output: Path, name: str) -> str:
    after = command(live, type="capture", name=name)
    event = wait_event(live, lambda item: item.get("type") == "capture"
                       and item.get("name") == name, after=after)
    destination = output / f"{name}.png"
    shutil.copy2(event["file"], destination)
    return str(destination)


def visual_outcome(events: list[dict], *, after: int) -> dict:
    relevant = [item for item in events[after:] if item.get("type") in
                ("state", "renderer", "transition-complete", "schedule", "test-error")]
    last = next((item for item in reversed(relevant) if item.get("type") == "renderer"), None)
    return {"events": relevant, "lastRenderer": last,
            "completions": [item for item in relevant if item.get("type") == "transition-complete"]}


def curate_race_evidence(raw: Path, output: Path) -> dict:
    report = json.loads((raw / "race-trace.json").read_text())
    output.mkdir(parents=True, exist_ok=True)
    names = ("running-gu-to-feng-before-cancel", "gu-running-after-cancel",
             "after-competing-states", "gu-review-after-consecutive")
    for name in names:
        shutil.copy2(raw / f"{name}.png", output / f"{name}.png")
    recording = raw / "reverse-request-window-recording.gif"
    if recording.is_file():
        shutil.copy2(recording, output / recording.name)
    full = report["cancelledTransition"].get("fullOperationEvents", [])
    debug = json.loads((raw / "race-events-debug.json").read_text())
    compact = {
        "cancelledTransition": {
            "lastRenderer": report["cancelledTransition"]["outcome"]["lastRenderer"],
            "completions": report["cancelledTransition"]["outcome"]["completions"],
            "fullOperationEvents": [item for item in full if item.get("type") in
                                    ("state", "renderer", "transition-complete")],
            "queuedRequests": [item for item in debug if item.get("type") == "form-request-queued"],
        },
        "competingStates": {
            "operationToken": report["competingStates"]["operationToken"],
            "completion": report["competingStates"]["completion"],
            "lastRenderer": report["competingStates"]["outcome"]["lastRenderer"],
        },
        "consecutiveTransitions": [
            {"at": item["at"], "expected": item["expected"], "completion": item["completion"]}
            for item in report["consecutiveTransitions"]
        ],
    }
    (output / "race-summary.json").write_text(json.dumps(compact, indent=2) + "\n")
    return compact


def curate_race_failure(raw: Path, output: Path) -> dict:
    """Retain observed first missing stage, not a fabricated successful trace."""
    events = json.loads((raw / "race-events-debug.json").read_text())
    relevant = [item for item in events if item.get("type") in (
        "state", "renderer", "transition-dwell-start", "transition-dwell-end",
        "transition-complete", "form-request-queued")]
    last_state = next(item for item in reversed(relevant) if item["type"] == "state")
    token, frame = last_state["operationToken"], last_state["frameIndex"]
    operation = [item for item in relevant if item.get("operationToken") == token]
    report = {"status": "LIVE_RACE_FAIL", "firstMissingObservedStage": "renderer post-paint acknowledgment",
              "rootCause": "HYPOTHESIS: renderer async/report scheduling; not proven",
              "lastPublishedFrame": frame, "operationToken": token,
              "completionObserved": any(item["type"] == "transition-complete" for item in operation),
              "framePaintObserved": any(item["type"] == "renderer"
                                        and item.get("transitionFrame") == frame for item in operation),
              "events": operation,
              "completedEarlierOperations": [item for item in relevant if item["type"] == "transition-complete"]}
    output.mkdir(parents=True, exist_ok=True)
    source = raw / "after-competing-states.png"
    if source.is_file():
        shutil.copy2(source, output / "stalled-after-competing-states.png")
    (output / "race-failure.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def audit(output: Path, executable: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="liang-race-audit-") as temporary:
        root = Path(temporary)
        for name in ("home", "tmp", "user-data"):
            (root / name).mkdir()
        env = {"HOME": str(root / "home"), "TMPDIR": str(root / "tmp") + os.sep,
               "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin"),
               "LANG": "en_US.UTF-8", "LNH_STANDALONE_TEST": "1",
               "LNH_DISABLE_CODEX_EVENTS": "1", "LNH_STANDALONE_TEST_ROOT": str(root),
               "LNH_TEST_INITIAL_TIME": "2026-09-14T08:59:00+08:00"}
        process = subprocess.Popen([str(executable), "--force-device-scale-factor=2"],
                                   cwd=ROOT, env=env, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, bufsize=1)
        live = LiveHarness(process)
        try:
            startup = wait_event(live, lambda item: item.get("type") == "startup", timeout=30)
            if startup.get("initialForm") != "gu":
                raise RuntimeError("QA2 did not start Gu")
            command(live, type="move", x=20, y=20)
            command(live, type="work", state="running")
            # At 09:00, Gu→Feng starts while Running is held. At frame 4,
            # jump the injected clock to 12:00: observe immediate cancellation
            # or the rework's full-sequence/latest-target deferred policy.
            start = command(live, type="clock", value="2026-09-14T09:00:00+08:00")
            wait_event(live, lambda item: item.get("type") == "renderer"
                       and item.get("transitionId") == "gu_to_feng"
                       and item.get("transitionFrame") == 4, after=start)
            mid = capture(live, output, "running-gu-to-feng-before-cancel")
            cancel = command(live, type="clock", value="2026-09-14T12:00:00+08:00")
            wait_event(live, lambda item: item.get("type") == "schedule"
                       and item.get("expectedForm") == "gu", after=cancel)
            captures = []
            deadline = time.monotonic() + 12
            while not any(item.get("type") == "renderer" and item.get("form") == "gu"
                          and item.get("visualMode") == "NORMAL" and item.get("row") == 7
                          for item in live.events[cancel:]):
                if time.monotonic() > deadline:
                    raise StandaloneQAError("reverse target did not settle to Gu Running")
                captures.append(screenshot(live, root, output, f"reverse-{len(captures):03d}"))
                time.sleep(0.045)
            if captures:
                video_gif(captures, output / "reverse-request-window-recording.gif")
            cancelled = capture(live, output, "gu-running-after-cancel")
            cancel_outcome = visual_outcome(live.events, after=cancel)
            # New afternoon peak, with competing work/interaction updates and
            # a duplicate target. The latest underlying state should survive.
            begin = command(live, type="clock", value="2026-09-14T14:00:00+08:00")
            frame = wait_event(live, lambda item: item.get("type") == "renderer"
                               and item.get("transitionId") == "gu_to_feng"
                               and item.get("transitionFrame") == 3, after=begin)
            token = frame.get("operationToken")
            command(live, type="form", form="feng")
            command(live, type="work", state="waiting")
            command(live, type="interaction", kind="hover", value=True)
            command(live, type="work", state="review")
            command(live, type="interaction", kind="hover", value=False)
            try:
                complete = wait_event(live, lambda item: item.get("type") == "transition-complete"
                                      and item.get("transitionId") == "gu_to_feng", after=begin, timeout=4)
            except StandaloneQAError:
                complete = None
            if complete is not None:
                normal = wait_event(live, lambda item: item.get("type") == "renderer"
                                    and item.get("form") == "feng" and item.get("visualMode") == "NORMAL"
                                    and item.get("row") == 8, after=begin)
            else:
                normal = None
            after = capture(live, output, "after-competing-states")
            race_outcome = visual_outcome(live.events, after=begin)
            # Recover by aligning with off-peak, then verify clean consecutive
            # directions separately from the competing-update failure.
            recover = command(live, type="clock", value="2026-09-14T18:00:00+08:00")
            wait_event(live, lambda item: item.get("type") == "schedule"
                       and item.get("expectedForm") == "gu", after=recover)
            if complete is not None:
                wait_event(live, lambda item: item.get("type") == "transition-complete"
                           and item.get("transitionId") == "feng_to_gu", after=recover, timeout=10)
            wait_event(live, lambda item: item.get("type") == "renderer"
                       and item.get("form") == "gu" and item.get("visualMode") == "NORMAL",
                       after=recover, timeout=10)
            consecutive = []
            for at, expected, transition_id in (
                ("2026-09-15T09:00:00+08:00", "feng", "gu_to_feng"),
                ("2026-09-15T12:00:00+08:00", "gu", "feng_to_gu"),
            ):
                start_index = command(live, type="clock", value=at)
                completion = wait_event(live, lambda item: item.get("type") == "transition-complete"
                                        and item.get("transitionId") == transition_id,
                                        after=start_index, timeout=10)
                wait_event(live, lambda item: item.get("type") == "renderer"
                           and item.get("form") == expected and item.get("visualMode") == "NORMAL"
                           and item.get("row") == 8, after=start_index)
                consecutive.append({"at": at, "expected": expected, "completion": completion,
                                    "outcome": visual_outcome(live.events, after=start_index)})
            end = capture(live, output, "gu-review-after-consecutive")
            report = {"startup": startup, "cancelledTransition": {
                        "beforeScreenshot": mid, "afterScreenshot": cancelled,
                        "outcome": cancel_outcome, "captures": captures,
                        "fullOperationEvents": list(live.events[start:cancel]) + cancel_outcome["events"]},
                      "competingStates": {"operationToken": token, "completion": complete,
                                          "normalRenderer": normal, "afterScreenshot": after,
                                          "outcome": race_outcome},
                      "consecutiveTransitions": consecutive,
                      "finalScreenshot": end}
            (output / "race-trace.json").write_text(json.dumps(report, indent=2) + "\n")
            return {"report": str(output / "race-trace.json"),
                    "competingStatesCompleted": complete is not None,
                    "finalForm": consecutive[-1]["completion"].get("form")}
        finally:
            (output / "race-events-debug.json").write_text(json.dumps(live.events, indent=2) + "\n")
            if process.poll() is None:
                live.send(type="quit")
                process.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--curated-output", type=Path)
    parser.add_argument("--executable", type=Path, default=QA2)
    args = parser.parse_args()
    if not args.executable.is_file():
        parser.error("QA2 executable missing")
    result = audit(args.output, args.executable)
    if args.curated_output:
        result["curated"] = curate_race_evidence(args.output, args.curated_output)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
