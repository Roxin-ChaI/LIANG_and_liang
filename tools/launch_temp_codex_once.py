#!/usr/bin/env python3
"""Launch one already-verified temporary Codex App with isolated file paths.

Never approves login/Keychain prompts, reads credentials, or starts the
production App. The PID and raw log stay in the ignored temporary directory.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.sign_minimal_temp_codex import BASELINE, SOURCE_APP, TEMP_APP, TEMP_ROOT, verify_signed_temp_app


def isolated_environment(root: Path) -> dict[str, str]:
    return {
        "HOME": str(root / "home"),
        "CODEX_HOME": str(root / "codex-home"),
        "CODEX_ELECTRON_USER_DATA_PATH": str(root / "user-data"),
        "TMPDIR": str(root / "runtime/tmp") + os.sep,
        "XDG_CONFIG_HOME": str(root / "home/.config"),
        "XDG_CACHE_HOME": str(root / "home/.cache"),
        "XDG_DATA_HOME": str(root / "home/.local/share"),
        "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin"),
        "LANG": os.environ.get("LANG", "en_US.UTF-8"),
        "ELECTRON_ENABLE_LOGGING": "1",
    }


def launch_once(root: Path = TEMP_ROOT, app: Path = TEMP_APP) -> dict[str, object]:
    if root.resolve() != TEMP_ROOT.resolve() or app.resolve() != TEMP_APP.resolve():
        raise ValueError("launch is restricted to the Phase 8F temporary App")
    marker = root / "launch-attempt.json"
    if marker.exists():
        raise ValueError("one controlled launch attempt has already been recorded")
    verify_signed_temp_app(SOURCE_APP, app, BASELINE, root)
    for directory in (root / "home", root / "codex-home", root / "user-data", root / "runtime/tmp", root / "logs"):
        if not directory.is_dir() or directory.is_symlink():
            raise ValueError("isolated temporary directory is missing or unsafe")
    executable = app / "Contents/MacOS/ChatGPT"
    if not executable.is_file() or executable.is_symlink():
        raise ValueError("temporary executable is missing")
    command = [str(executable), f"--user-data-dir={root / 'user-data'}", "--no-first-run"]
    environment = isolated_environment(root)
    log = root / "logs/launch.log"
    # This marker is intentionally written before Popen, preventing an
    # accidental second attempt after an uncertain launch response.
    marker.write_text(json.dumps({"status": "ATTEMPT_STARTED", "executable": str(executable)}) + "\n")
    with log.open("wb") as handle:
        process = subprocess.Popen(command, cwd=root, env=environment, stdout=handle,
                                   stderr=subprocess.STDOUT, start_new_session=True)
    time.sleep(8)
    socket_path = root / "runtime/tmp" / f"liang-no-henshin-{os.getuid()}" / "runtime.sock"
    result = {
        "status": "PROCESS_ALIVE" if process.poll() is None else "PROCESS_EXITED",
        "pid": process.pid,
        "exitCode": process.poll(),
        "bridgeSocketExists": socket_path.is_socket(),
        "bridgeSocket": str(socket_path),
        "logPath": str(log),
        "keychainIsolationProven": False,
    }
    marker.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def main() -> int:
    try:
        result = launch_once()
    except Exception as error:
        print(json.dumps({"status": "BLOCKED", "reason": str(error)}))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PROCESS_ALIVE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
