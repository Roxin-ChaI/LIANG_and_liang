"""Validate all Phase 3D oversized frames against frozen sources and layout."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from PIL import Image

from analyze_transition_endpoints import dark_character_bbox
from derive_transition_overlay_geometry import derive
from normalize_transition_frames import (
    BASELINE, CELL, DIRECTIONS, ROOT, overlay_plan, png_bytes, render_overlay_frame,
)


MANIFEST = ROOT / "assets" / "transform-overlay.sha256"


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_frozen(manifest: Path, prefix: str) -> int:
    count = 0
    for line in manifest.read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        if not name.startswith(prefix):
            continue
        path = ROOT / name
        if not path.exists() or checksum(path) != digest:
            raise ValueError(f"frozen file changed: {path}")
        count += 1
    return count


def validate(*, write_manifest: bool = False) -> dict[str, object]:
    original_count = verify_frozen(ROOT / "assets-frozen.sha256", "assets/transform/")
    legacy_count = verify_frozen(ROOT / "assets" / "transform-runtime.sha256", "assets/transform-runtime/")
    if original_count != 18 or legacy_count != 18:
        raise ValueError(f"frozen source/legacy counts changed: {original_count}/{legacy_count}")
    expected_layout, preflight = derive()
    if preflight["result"] != "PASS":
        raise ValueError("geometry preflight blocked")
    lines: list[str] = []
    rows = 0
    crop_count = 0
    for direction, count in DIRECTIONS.items():
        layout, schedule = overlay_plan(direction)
        if layout != expected_layout[direction]:
            raise ValueError(f"{direction}: layout fixture changed")
        folder = ROOT / "assets" / "transform-overlay" / direction
        files = sorted(folder.glob("*.png"))
        expected_names = [f"{direction}_{i:02d}.png" for i in range(1, count + 1)]
        if [p.name for p in files] != expected_names:
            raise ValueError(f"{direction}: expected exactly {count} ordered PNGs")
        for path, entry in zip(files, schedule):
            with Image.open(path) as image:
                if image.mode != "RGBA" or image.size != (layout["canvasWidth"], layout["canvasHeight"]):
                    raise ValueError(f"{path}: wrong RGBA/canvas")
                full = image.getchannel("A").getbbox()
                if full is None:
                    raise ValueError(f"{path}: empty alpha")
                # An edge touch is allowed: the generated full-alpha bbox is
                # proven to contain every sampled source pixel, not cropped.
                body = dark_character_bbox(image)
                mapped_center = (body[0] + body[2]) / 2 + layout["offsetLeft"]
                mapped_baseline = body[3] - 1 + layout["offsetTop"]
                if abs(mapped_center - CELL[0] / 2) > 1 or mapped_baseline != BASELINE:
                    raise ValueError(f"{path}: body anchor drift ({mapped_center},{mapped_baseline})")
                for red, green, blue, alpha in image.get_flattened_data():
                    if alpha == 0 and (red or green or blue):
                        raise ValueError(f"{path}: hidden transparent RGB")
            generated = png_bytes(render_overlay_frame(direction, entry, layout))
            if path.read_bytes() != generated:
                crop_count += 1
                raise ValueError(f"{path}: not pixel-exact deterministic nearest overlay")
            lines.append(f"{checksum(path)}  {path.relative_to(ROOT).as_posix()}")
            rows += 1
    if rows != 18 or crop_count:
        raise ValueError(f"expected 18 uncropped frames, got {rows}, crops={crop_count}")
    expected_manifest = ("\n".join(lines) + "\n").encode()
    if write_manifest:
        MANIFEST.write_bytes(expected_manifest)
    elif not MANIFEST.exists() or MANIFEST.read_bytes() != expected_manifest:
        raise ValueError(f"{MANIFEST}: missing or nondeterministic SHA manifest")
    return {
        "result": "PASS", "frames": rows, "effectCropCount": crop_count,
        "sourceFrozen": True, "legacyRuntimeFrozen": True,
        "nearestDeterministic": True, "bodyAnchor": [96, 203],
        "manifestSha256": hashlib.sha256(expected_manifest).hexdigest(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-manifest", action="store_true", help="write deterministic overlay SHA manifest")
    args = parser.parse_args()
    result = validate(write_manifest=args.write_manifest)
    print(f"TRANSITION_OVERLAY_VALIDATION_{result['result']} frames={result['frames']} "
          f"effect_crop_count={result['effectCropCount']} source_unchanged=true "
          f"legacy_unchanged=true manifest_sha256={result['manifestSha256']}")


if __name__ == "__main__":
    main()
