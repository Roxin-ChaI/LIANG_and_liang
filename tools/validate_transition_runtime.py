"""Validate frozen, deterministic 192x208 transition derivatives and sources."""

from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image

from normalize_transition_frames import (
    BASELINE, CELL, DIRECTIONS, ROOT, normalize, plan_sequence,
)


def read_manifest(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in path.read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        digest, relative = line.split(maxsplit=1)
        if len(digest) != 64 or relative in entries:
            raise ValueError(f"{path}: malformed or duplicate entry: {line}")
        entries[relative] = digest
    return entries


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate() -> dict[str, object]:
    originals = read_manifest(ROOT / "assets-frozen.sha256")
    runtime = read_manifest(ROOT / "assets" / "transform-runtime.sha256")
    expected_runtime: set[str] = set()
    checked_sources = checked_outputs = 0
    centers: list[float] = []
    scales: set[float] = set()
    for direction, count in DIRECTIONS.items():
        plan = plan_sequence(direction)
        if len(plan.source_paths) != count:
            raise ValueError(f"{direction}: wrong source count")
        scales.add(plan.scale)
        normalize(direction, check=True)  # Byte-for-byte regeneration check.
        for index, source in enumerate(plan.source_paths, start=1):
            if source.name != f"{direction}_{index:02d}.png":
                raise ValueError(f"{direction}: frame order/name mismatch: {source.name}")
            source_rel = source.relative_to(ROOT).as_posix()
            if originals.get(source_rel) != sha256(source):
                raise ValueError(f"approved source hash changed: {source_rel}")
            checked_sources += 1
            output = ROOT / "assets" / "transform-runtime" / direction / source.name
            relative = output.relative_to(ROOT).as_posix()
            expected_runtime.add(relative)
            if runtime.get(relative) != sha256(output):
                raise ValueError(f"runtime hash mismatch: {relative}")
            with Image.open(output) as image:
                if image.format != "PNG" or image.mode != "RGBA" or image.size != CELL:
                    raise ValueError(f"{relative}: not 192x208 RGBA PNG")
                bbox = image.getchannel("A").getbbox()
                if bbox is None or bbox[3] - 1 != BASELINE:
                    raise ValueError(f"{relative}: empty or unstable alpha baseline")
                if bbox[0] < 2 or bbox[2] > CELL[0] - 2 or bbox[1] < 2:
                    raise ValueError(f"{relative}: unsafe edge or potential clipping: {bbox}")
                center = (bbox[0] + bbox[2]) / 2
                if not 95.5 <= center <= 96.5:
                    raise ValueError(f"{relative}: center drift: {center}")
                centers.append(center)
                if any(alpha == 0 and (red or green or blue)
                       for red, green, blue, alpha in image.get_flattened_data()):
                    raise ValueError(f"{relative}: hidden RGB under transparent alpha")
            checked_outputs += 1
    actual_runtime = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "assets" / "transform-runtime").glob("*/*.png")
    }
    if set(runtime) != expected_runtime or actual_runtime != expected_runtime:
        raise ValueError("runtime manifest/files are not exactly the expected 18 frames")
    if len(scales) != 1:
        raise ValueError(f"different transition scales: {scales}")
    return {
        "result": "NORMALIZATION_PASS",
        "source_hashes_unchanged": checked_sources == 18,
        "runtime_hashes_frozen": checked_outputs == 18,
        "deterministic_regeneration": True,
        "frames": checked_outputs,
        "size": "192x208",
        "baseline": BASELINE,
        "center_range": [min(centers), max(centers)],
        "scale": next(iter(scales)),
        "visual_review_required": True,
    }


def main() -> None:
    import json

    print(json.dumps(validate(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
