"""Capture all seven integrated states from the real project-owned Electron app."""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.assemble_approved_actions import OUT, ROWS
from tools.build_standalone_app import source_files, sha256
from tools.run_standalone_app_qa import LiveHarness, command, wait_event, capture

APP = ROOT / "dist/Liang no Henshin Integrated 2026-10-24.app"
EVIDENCE = ROOT / "standalone-app/evidence/integrated-seven-actions-2026-10-24"


def run():
    if EVIDENCE.exists():
        raise FileExistsError("Preserve earlier live evidence")
    EVIDENCE.mkdir(parents=True)
    payload = APP / "Contents/Resources/app"
    for source, relative in source_files():
        if sha256(source) != sha256(payload / relative):
            raise ValueError(f"Bundle differs from selected input: {relative}")
    results = []
    with tempfile.TemporaryDirectory(prefix="lnh-seven-actions-") as temporary:
        root = Path(temporary)
        (root / "user-data").mkdir()
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "en_US.UTF-8",
               "LNH_STANDALONE_TEST": "1", "LNH_DISABLE_CODEX_EVENTS": "1",
               "LNH_STANDALONE_TEST_ROOT": str(root), "LNH_TEST_INITIAL_TIME": "2026-09-14T08:59:00+08:00"}
        process = subprocess.Popen([str(APP/"Contents/MacOS/Electron")], cwd=ROOT, env=env,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, bufsize=1)
        live = LiveHarness(process)
        try:
            wait_event(live, lambda e: e.get("type") == "startup", timeout=30)
            command(live, type="move", x=20, y=20)
            command(live, type="interaction", kind="hover", value=False)
            command(live, type="interaction", kind="look", value=None)
            for form, row, state, *_ in ROWS:
                command(live, type="interaction", kind="drag", value=None)
                command(live, type="work", state="idle")
                command(live, type="form", form=form, animate=False)
                after = command(live, **({"type":"interaction", "kind":"drag", "value":state}
                                        if row in (1,2) else {"type":"work", "state":state}))
                count = next(r["frames"] for r in json.loads((OUT/"manifest.json").read_text())["replacements"] if r["form"]==form and r["row"]==row)
                deadline = time.monotonic() + 8
                while time.monotonic() < deadline:
                    events = [e for e in live.events[after:] if e.get("type")=="renderer" and e.get("form")==form and e.get("row")==row]
                    if {e["frame"] for e in events} == set(range(count)):
                        break
                    time.sleep(.025)
                else:
                    raise RuntimeError(f"Incomplete live frame coverage {form}/{state}")
                shot = capture(live, f"{form}-{state}", EVIDENCE)
                results.append({"form":form,"state":state,"framesObserved":sorted({e["frame"] for e in events}),
                                "screenshot":Path(shot).name,"rendererEvents":events})
        finally:
            if process.poll() is None:
                live.send(type="quit")
                process.wait(timeout=10)
            (EVIDENCE/"events.json").write_text(json.dumps(live.events, indent=2)+"\n")
    report = {"status":"SEVEN_ACTIONS_RENDERER_PASS", "bundleInputsExact":True,
              "results":results, "testProcessExited":process.poll() is not None,
              "physicalMouse":"NOT_VERIFIED", "liveCodexHook":"NOT_TESTED_DISABLED_FOR_ISOLATION"}
    (EVIDENCE/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"status":report["status"],"evidence":str(EVIDENCE)}))


if __name__ == "__main__":
    run()
