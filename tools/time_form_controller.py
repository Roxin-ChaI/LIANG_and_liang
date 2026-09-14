#!/usr/bin/env python3
"""Select the Liang no Henshin atlas for the current Shanghai time.

The controller owns only the active ``spritesheet.webp``. It never edits the
pet manifest, the selected avatar setting, or the Codex Desktop application.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, time
from pathlib import Path
from typing import Mapping
from zoneinfo import ZoneInfo

SHANGHAI = ZoneInfo("Asia/Shanghai")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ATLASES = {
    "gu": PROJECT_ROOT / "assets" / "builds" / "gu" / "spritesheet.webp",
    "feng": PROJECT_ROOT / "assets" / "builds" / "feng" / "spritesheet.webp",
}
DEFAULT_ACTIVE_ATLAS = (
    Path.home() / ".codex" / "pets" / "liang-no-henshin" / "spritesheet.webp"
)
REFRESH_INSTRUCTION = "Settings > Pets > Refresh"


class ControllerError(RuntimeError):
    """Raised when the active atlas cannot be selected safely."""


@dataclass(frozen=True)
class ControllerStatus:
    """Machine-readable result of one controller invocation."""

    current_time: str
    expected_form: str
    current_form: str
    switched: bool
    refresh_required: bool
    refresh_instruction: str | None


def sha256(path: Path) -> str:
    """Return the SHA256 digest for *path*."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def shanghai_time(value: datetime | None = None) -> datetime:
    """Normalize a datetime to Asia/Shanghai, or read the current time."""

    if value is None:
        return datetime.now(SHANGHAI)
    if value.tzinfo is None:
        return value.replace(tzinfo=SHANGHAI)
    return value.astimezone(SHANGHAI)


def expected_form_at(value: datetime) -> str:
    """Return ``feng`` during weekday peak windows, otherwise ``gu``."""

    current = shanghai_time(value)
    clock = current.time().replace(tzinfo=None)
    is_weekday = current.weekday() < 5
    is_morning_peak = time(9, 0) <= clock < time(12, 0)
    is_afternoon_peak = time(14, 0) <= clock < time(18, 0)
    return "feng" if is_weekday and (is_morning_peak or is_afternoon_peak) else "gu"


def _validated_source_hashes(atlases: Mapping[str, Path]) -> dict[str, str]:
    if set(atlases) != {"gu", "feng"}:
        raise ControllerError("atlas mapping must contain exactly gu and feng")

    hashes: dict[str, str] = {}
    for form in ("gu", "feng"):
        source = Path(atlases[form])
        if not source.is_file():
            raise ControllerError(f"{form} atlas not found: {source}")
        hashes[form] = sha256(source)

    if hashes["gu"] == hashes["feng"]:
        raise ControllerError("gu and feng atlases unexpectedly have the same SHA256")
    return hashes


def identify_form(active_atlas: Path, source_hashes: Mapping[str, str]) -> str:
    """Identify the active atlas by SHA256, returning ``unknown`` if unmatched."""

    if not active_atlas.is_file():
        return "unknown"
    active_hash = sha256(active_atlas)
    for form in ("gu", "feng"):
        if active_hash == source_hashes[form]:
            return form
    return "unknown"


def atomic_replace(source: Path, destination: Path, expected_sha256: str) -> None:
    """Copy *source* into place atomically after pre- and post-replace checks."""

    if not destination.parent.is_dir():
        raise ControllerError(f"active pet directory not found: {destination.parent}")

    fd, temporary_name = tempfile.mkstemp(
        dir=str(destination.parent), prefix=f".{destination.name}.", suffix=".tmp"
    )
    temporary = Path(temporary_name)
    try:
        with source.open("rb") as source_handle, os.fdopen(fd, "wb") as output_handle:
            shutil.copyfileobj(source_handle, output_handle, length=1 << 20)
            output_handle.flush()
            os.fsync(output_handle.fileno())

        mode = destination.stat().st_mode & 0o777 if destination.exists() else 0o644
        os.chmod(temporary, mode)
        if sha256(temporary) != expected_sha256:
            raise ControllerError("temporary atlas SHA256 verification failed")

        os.replace(temporary, destination)
        if sha256(destination) != expected_sha256:
            raise ControllerError("installed atlas SHA256 verification failed")
    except Exception:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise


def run_controller(
    *,
    now: datetime | None = None,
    atlases: Mapping[str, Path] = DEFAULT_ATLASES,
    active_atlas: Path = DEFAULT_ACTIVE_ATLAS,
) -> ControllerStatus:
    """Evaluate the schedule and switch the atlas only when necessary."""

    current_time = shanghai_time(now)
    expected_form = expected_form_at(current_time)
    source_paths = {form: Path(path) for form, path in atlases.items()}
    source_hashes = _validated_source_hashes(source_paths)
    form_before = identify_form(active_atlas, source_hashes)
    switched = form_before != expected_form

    if switched:
        atomic_replace(
            source_paths[expected_form], active_atlas, source_hashes[expected_form]
        )

    current_form = identify_form(active_atlas, source_hashes)
    if current_form != expected_form:
        raise ControllerError(
            f"active atlas verification failed: expected {expected_form}, got {current_form}"
        )

    return ControllerStatus(
        current_time=current_time.isoformat(timespec="seconds"),
        expected_form=expected_form,
        current_form=current_form,
        switched=switched,
        refresh_required=switched,
        refresh_instruction=REFRESH_INSTRUCTION if switched else None,
    )


def parse_time(value: str) -> datetime:
    """Parse an ISO-8601 test time; naive values are interpreted in Shanghai."""

    try:
        return shanghai_time(datetime.fromisoformat(value))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid ISO-8601 datetime: {value}") from exc


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Switch Liang no Henshin between Gu and Feng by Shanghai time."
    )
    parser.add_argument(
        "--at",
        type=parse_time,
        help="ISO-8601 time override for deterministic testing (default: now)",
    )
    parser.add_argument("--gu-atlas", type=Path, default=DEFAULT_ATLASES["gu"])
    parser.add_argument("--feng-atlas", type=Path, default=DEFAULT_ATLASES["feng"])
    parser.add_argument("--active-atlas", type=Path, default=DEFAULT_ACTIVE_ATLAS)
    args = parser.parse_args()

    try:
        status = run_controller(
            now=args.at,
            atlases={"gu": args.gu_atlas, "feng": args.feng_atlas},
            active_atlas=args.active_atlas,
        )
    except (ControllerError, OSError) as exc:
        raise SystemExit(f"controller error: {exc}") from exc

    print(json.dumps(asdict(status), ensure_ascii=False))


if __name__ == "__main__":
    main()
