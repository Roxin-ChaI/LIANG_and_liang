"""Package ten generated art poses for review, preserving their original pixels.

This does not create runtime-ready sprites, replace Idle endpoints, harden alpha,
or approve the artwork. Grid crops are checked against visible character bounds;
all source alpha/RGB, including faint edge remnants, is retained in the crops.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets/rework/v0.1.0/gu-to-feng-idle-redraw-2026-10-01"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    source = OUT / "source-sheet.png"
    source_hash = sha(source)
    with Image.open(source) as image:
        if image.mode != "RGBA":
            raise ValueError("expected actual RGBA source")
        raw = image.copy()
    width, height = raw.size
    cw, ch = (width + 4) // 5, (height + 1) // 2
    poses, records = [], []
    for index in range(10):
        col, row = index % 5, index // 5
        rect = (col * width // 5, row * height // 2,
                (col + 1) * width // 5, (row + 1) * height // 2)
        crop = raw.crop(rect)
        visible = crop.getchannel("A").point(lambda a: 255 if a >= 128 else 0).getbbox()
        if visible is None or min(visible[:2]) <= 0 or visible[2] >= crop.width or visible[3] >= crop.height:
            raise ValueError(f"visible art touches extraction border: {index + 1}")
        # Padding only: no transform, sampling, recoloring or endpoint insertion.
        padded = Image.new("RGBA", (cw, ch))
        padded.paste(crop, (0, 0))
        if padded.crop((0, 0, crop.width, crop.height)).tobytes() != crop.tobytes():
            raise AssertionError("source pixel preservation failed")
        pixels = list(padded.get_flattened_data())
        poses.append(padded)
        records.append({
            "frame": index + 1, "sourceRect": list(rect), "canvas": [cw, ch],
            "visibleAlpha128Bbox": list(visible), "originalPixelsPreserved": True,
            "partialAlphaPixels": sum(0 < p[3] < 255 for p in pixels),
            "hiddenRgbPixels": sum(any(p[:3]) for p in pixels if p[3] == 0),
            "idleInserted": False, "scaling": None,
        })

    targets = [OUT / "frames", OUT / "contact-sheet.png", OUT / "review.json"]
    if any(path.exists() for path in targets):
        raise ValueError("refuse to overwrite existing candidate review")
    targets[0].mkdir()
    contact = Image.new("RGBA", (5 * cw, 2 * (ch + 24)), (35, 35, 39, 255))
    draw = ImageDraw.Draw(contact)
    for index, (pose, record) in enumerate(zip(poses, records)):
        file = targets[0] / f"gu_to_feng_{index + 1:02d}.png"
        pose.save(file)
        with Image.open(file) as saved:
            if saved.tobytes() != pose.tobytes():
                raise AssertionError("saved PNG differs from extracted pixels")
        record.update(path=str(file.relative_to(ROOT)), sha256=sha(file))
        x, y = (index % 5) * cw, (index // 5) * (ch + 24)
        draw.text((x + 8, y + 5), f"{index + 1:02d} / ART CANDIDATE", fill="white")
        contact.alpha_composite(pose, (x, y + 24))
    contact.save(targets[1])
    report = {
        "status": "ART_CANDIDATE_NOT_APPROVED", "date": "2026-10-01",
        "generator": "built-in image_gen", "selectedAttempt": 2,
        "sourceSha256": source_hash, "sourceSize": list(raw.size),
        "transitionFrameCount": 10, "idleFrameCount": 0,
        "runtimeEligible": False, "appIntegrated": False,
        "visualApproval": "PENDING_USER_REVIEW",
        "idleStyleExactMatch": "NOT_CONFIRMED",
        "hardEdgeAlphaPass": all(r["partialAlphaPixels"] == 0 for r in records),
        "notes": [
            "Frames are lossless raw art crops, not 224x240 runtime sprites.",
            "The original alpha is preserved; partial-alpha edges require further art preparation.",
            "The candidate still needs native-scale identity/proportion and animation continuity approval.",
            "The selected second attempt improved gutters; the third attempt made early Gu too stern.",
            "Idle is not copied into the ten-frame animation. No reverse-direction asset was edited.",
        ], "frames": records,
    }
    targets[2].write_text(json.dumps(report, indent=2) + "\n")
    if sha(source) != source_hash:
        raise AssertionError("source modified")
    print(json.dumps({k: report[k] for k in (
        "status", "transitionFrameCount", "idleFrameCount", "hardEdgeAlphaPass", "runtimeEligible"
    )}))


if __name__ == "__main__":
    main()
