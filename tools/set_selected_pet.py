#!/usr/bin/env python3
"""Set or remove desktop.selected-avatar-id in ~/.codex/config.toml safely.

Usage:
  set_selected_pet.py custom:liang-gu   # set key
  set_selected_pet.py --remove          # remove key entirely

The file is parsed with tomllib before and after the edit. Only the single
selected-avatar-id line is inserted or replaced; all other lines are kept
byte-for-byte.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import tomllib
from pathlib import Path

CONFIG = Path.home() / ".codex" / "config.toml"
KEY = "selected-avatar-id"
SECTION = "[desktop]"


def tomllib_value(value: str) -> str:
    """Encode a string as a TOML basic string using JSON quoting rules."""
    return json.dumps(value, ensure_ascii=False)


def main() -> None:
    args = [a for a in sys.argv[1:] if a]
    remove = "--remove" in args
    values = [a for a in args if a != "--remove"]
    if remove and values:
        raise SystemExit("cannot combine --remove with a value")
    if not remove and len(values) != 1:
        raise SystemExit("expected one pet id or --remove")
    new_value = None if remove else values[0]

    original_bytes = CONFIG.read_bytes()
    original_text = original_bytes.decode("utf-8")
    before = tomllib.loads(original_text)
    lines = original_text.splitlines(keepends=True)

    header_idx = None
    section_end = len(lines)
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if header_idx is None:
            if stripped == SECTION or stripped.startswith(SECTION + " "):
                header_idx = idx
            continue
        # Next table header closes the [desktop] section.
        if stripped.startswith("["):
            section_end = idx
            break
    if header_idx is None:
        raise SystemExit("[desktop] table not found")

    key_pat = re.compile(r"^\s*" + re.escape(KEY) + r"\s*=")
    key_idx = None
    for idx in range(header_idx + 1, section_end):
        if key_pat.match(lines[idx]):
            key_idx = idx
            break

    if remove:
        if key_idx is not None:
            del lines[key_idx]
    else:
        assert new_value is not None
        new_line = f'{KEY} = {tomllib_value(new_value)}\n'
        if key_idx is not None:
            lines[key_idx] = new_line
        else:
            lines.insert(header_idx + 1, new_line)

    result_text = "".join(lines)
    after = tomllib.loads(result_text)
    after_desktop = after.get("desktop", {})
    if remove:
        if KEY in after_desktop:
            raise SystemExit("key still present after removal")
        expected_ok = True
    else:
        assert new_value is not None
        expected_ok = after_desktop.get(KEY) == new_value
    if not expected_ok:
        raise SystemExit("re-parse validation failed")

    fd, tmp_name = tempfile.mkstemp(
        dir=str(CONFIG.parent), prefix=".config.toml.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(result_text)
        os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, CONFIG)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise

    # Final independent verification against the on-disk file.
    final_text = CONFIG.read_text(encoding="utf-8")
    final = tomllib.loads(final_text)
    final_desktop = final.get("desktop", {})
    if remove:
        assert KEY not in final_desktop
    else:
        assert new_value is not None
        assert final_desktop.get(KEY) == new_value
    print(json.dumps({"ok": True, "remove": remove, "value": new_value}))


if __name__ == "__main__":
    main()
