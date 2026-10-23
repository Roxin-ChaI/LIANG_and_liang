"""Exact per-cell mirror of the approved right walk; no drawing or resampling."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build_animation_review import save_contact, save_preview, sha256

SOURCE = ROOT / "assets/rework/v0.1.0/feng-walk-right-eight-2026-10-23"
OUT = ROOT / "assets/rework/v0.1.0/feng-walk-left-eight-2026-10-23"


def verified_frames(source=SOURCE):
    approval = json.loads((source / "review-status.json").read_text())
    if (approval["status"] != "FENG_RIGHT_WALK_ART_APPROVED"
            or approval["userApproval"] != "APPROVED"
            or approval["approvedRevision"] != "review-r2"):
        raise ValueError("Approved R2 right walk required")
    for path, digest in approval["sha256"].items():
        if sha256(source / path) != digest:
            raise ValueError(f"Frozen source changed: {path}")
    frames = []
    for i in range(1, 9):
        path = source / "review-r2" / f"right-{i:02d}.png"
        if str(path.relative_to(source)) not in approval["sha256"]:
            raise ValueError("Frame missing from frozen manifest")
        with Image.open(path) as im:
            if im.mode != "RGBA" or im.size != (192, 208):
                raise ValueError("192x208 RGBA source required")
            frames.append(im.copy())
    return frames


def mirror_frames(frames):
    if len(frames) != 8 or any(f.mode != "RGBA" or f.size != (192, 208) for f in frames):
        raise ValueError("Exactly eight 192x208 RGBA frames required")
    # Flip each cell, never the whole strip: temporal order remains unchanged.
    return [f.transpose(Image.Transpose.FLIP_LEFT_RIGHT) for f in frames]


def build(folder=OUT, source=SOURCE):
    if folder.exists():
        raise FileExistsError("Do not overwrite review artwork")
    right = verified_frames(source)
    left = mirror_frames(right)
    metrics = []
    for i, (r, l) in enumerate(zip(right, left), 1):
        pixels = np.array(l)
        if set(np.unique(pixels[:, :, 3])) - {0, 255} or np.any(pixels[pixels[:, :, 3] == 0, :3]):
            raise ValueError("Unexpected alpha or hidden RGB")
        x, y, end_x, end_y = l.getbbox()
        if x < 2 or y < 2 or end_x > 190 or end_y != 204:
            raise ValueError("Clipping, insufficient margin or baseline mismatch")
        assert np.array_equal(pixels, np.array(r)[:, ::-1, :])
        metrics.append({"frame": i, "sourceFrame": i, "bbox": list(l.getbbox()),
                        "baseline": 203, "exactMirror": True,
                        "sourceSha256": sha256(source / "review-r2" / f"right-{i:02d}.png")})
    folder.mkdir(parents=True)
    strip = Image.new("RGBA", (1536, 208))
    comparisons = []
    for i, (r, l) in enumerate(zip(right, left), 1):
        l.save(folder / f"left-{i:02d}.png")
        strip.paste(l, ((i - 1) * 192, 0))
        comparison = Image.new("RGBA", (384, 208))
        comparison.paste(r, (0, 0))
        comparison.paste(l, (192, 0))
        comparisons.append(comparison)
    strip.save(folder / "feng-running-left.png")
    save_preview(left, [140] * 8, folder / "preview.gif")
    save_preview(left, [450] * 8, folder / "preview-slow.gif")
    save_preview(left, [140] * 8, folder / "preview-native.gif", display_size=(192, 208))
    save_preview(comparisons, [140] * 8, folder / "right-left-comparison.gif", display_size=(768, 416))
    save_contact(left, folder / "contact.png", columns=4)
    save_contact(comparisons, folder / "right-left-contact.png", columns=2)
    # Compare every temporal edge including frame 8 -> 1; mirroring cannot
    # improve existing gait defects, but must not add or reverse any differences.
    edges = []
    for i in range(8):
        j = (i + 1) % 8
        rdiff = np.any(np.array(right[i]) != np.array(right[j]), axis=2)
        ldiff = np.any(np.array(left[i]) != np.array(left[j]), axis=2)
        assert np.array_equal(ldiff, rdiff[:, ::-1])
        edges.append({"from": i + 1, "to": j + 1, "changedPixels": int(ldiff.sum()),
                      "sameTemporalDifferenceAsSource": True})
    report = {"structuralStatus": "PASS", "userApproval": "PENDING", "runtimeIntegrated": False,
              "source": str(source.relative_to(ROOT)),
              "sourceApprovalSha256": sha256(source / "review-status.json"),
              "method": "Per-frame exact horizontal pixel reflection x -> 191-x. No scaling, translation, interpolation, recoloring or frame reordering.",
              "frameCount": 8, "cell": [192, 208], "strip": [1536, 208],
              "durationMs": [140] * 8, "frames": metrics, "edges": edges,
              "limitations": "Source artwork's accepted height/gait variations are inherited, not fixed. A source x=96 pixel maps to x=95, around cell axis95.5; no compensating translation.",
              "appTest": "NOT_TESTED",
              "sha256": {p.name: sha256(p) for p in sorted(folder.iterdir()) if p.is_file()}}
    (folder / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
