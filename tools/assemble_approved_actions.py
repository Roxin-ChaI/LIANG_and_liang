"""Integrate only seven approved rows into copies of the current selected atlases."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build_animation_review import sha256, save_preview, save_contact

ART = ROOT / "assets/rework/v0.1.0"
OUT = ART / "approved-actions-integration-2026-10-23"
BASE = ART / "action-repair-2026-10-02"
# form, row, state, source folder, strip, approval folder, per-item approval
ROWS = [
    ("gu", 1, "running-right", "gu-drag-right-suspended-2026-10-21/revision-2", "gu-running-right.png", None, None),
    ("gu", 2, "running-left", "gu-drag-left-suspended-2026-10-22", "gu-running-left.png", None, None),
    ("feng", 1, "running-right", "feng-walk-right-eight-2026-10-23/review-r2", "feng-running-right.png", "feng-walk-right-eight-2026-10-23", None),
    ("feng", 2, "running-left", "feng-walk-left-eight-2026-10-23", "feng-running-left.png", None, None),
    ("feng", 3, "waving", "action-rework-r2-2026-10-03/feng-waving-edge", "feng-waving-edge.png", "action-rework-r2-2026-10-03", "feng-waving-edge"),
    ("feng", 5, "failed", "feng-failed-r3-2026-10-20/nod-revision", "feng-failed.png", None, None),
    ("feng", 8, "review", "action-rework-r2-2026-10-03/feng-review-edge", "feng-review-edge.png", "action-rework-r2-2026-10-03", "feng-review-edge"),
]
COUNTS = [6, 8, 8, 4, 5, 8, 6, 6, 6, 8, 8]


def approved_input(spec):
    form, row, state, directory, filename, approval_directory, item = spec
    folder = ART / directory
    approval_root = ART / (approval_directory or directory)
    approval_path = approval_root / "review-status.json"
    approval = json.loads(approval_path.read_text())
    path = folder / filename
    if item:
        decision = approval["items"][item]
        if decision["status"] != "USER_APPROVED" or sha256(path) != decision["stripSha256"]:
            raise ValueError("Unapproved or changed strip")
    else:
        if approval["userApproval"] != "APPROVED":
            raise ValueError("Unapproved art")
        relative = str(path.relative_to(approval_root))
        if relative not in approval["sha256"]:
            raise ValueError("Strip absent from frozen approval")
        for name, digest in approval["sha256"].items():
            if sha256(approval_root / name) != digest:
                raise ValueError(f"Frozen art changed: {name}")
    with Image.open(path) as im:
        if im.mode != "RGBA" or im.size != (192 * COUNTS[row], 208):
            raise ValueError("Unexpected strip mode/size")
        strip = im.copy()
    with Image.open(folder / "preview.gif") as gif:
        if gif.n_frames != COUNTS[row]:
            raise ValueError("Approved preview count mismatch")
        durations = []
        for i in range(gif.n_frames):
            gif.seek(i)
            durations.append(gif.info["duration"])
    return strip, {"form": form, "row": row, "state": state, "frames": COUNTS[row],
                   "source": str(path.relative_to(ROOT)), "sourceSha256": sha256(path),
                   "approval": str(approval_path.relative_to(ROOT)),
                   "approvalSha256": sha256(approval_path), "durationsMs": durations}


def validate_atlas(im, *, preserved_unused=frozenset({(0, 6)})):
    if im.mode != "RGBA" or im.size != (1536, 2288):
        raise ValueError("V2 geometry mismatch")
    pixels = np.array(im)
    if np.any(pixels[pixels[:, :, 3] == 0, :3]):
        raise ValueError("Hidden RGB")
    for row, count in enumerate(COUNTS):
        for col in range(8):
            cell = im.crop((col*192, row*208, (col+1)*192, (row+1)*208))
            box = cell.getbbox()
            if col >= count:
                if any(cell.tobytes()) and (row, col) not in preserved_unused:
                    raise ValueError("Unused cell must be RGBA zero")
            elif box is None or box[0] <= 0 or box[1] <= 0 or box[2] >= 192 or box[3] >= 208:
                raise ValueError(f"Empty or edge-touching cell {row}/{col}")


def build(output=OUT):
    if output.exists():
        raise FileExistsError("Integration output is immutable")
    originals = {form: Image.open(BASE / f"{form}.webp").convert("RGBA") for form in ("gu", "feng")}
    atlases = {form: im.copy() for form, im in originals.items()}
    records = []
    inputs = []
    for spec in ROWS:
        strip, record = approved_input(spec)
        if set(np.unique(np.array(strip)[:, :, 3])) - {0, 255}:
            raise ValueError("Approved replacement must use binary alpha")
        form, row = record["form"], record["row"]
        atlases[form].paste((0, 0, 0, 0), (0, row*208, 1536, (row+1)*208))
        atlases[form].paste(strip, (0, row*208))  # copy RGBA, never alpha blend
        records.append(record)
        inputs.append(strip)
    for form, im in atlases.items():
        validate_atlas(im)
        changed_rows = {r["row"] for r in records if r["form"] == form}
        for row in set(range(11)) - changed_rows:
            box = (0, row*208, 1536, (row+1)*208)
            assert im.crop(box).tobytes() == originals[form].crop(box).tobytes()
    output.mkdir(parents=True)
    for form, im in atlases.items():
        path = output / f"{form}.webp"
        im.save(path, lossless=True, exact=True, method=6)
        with Image.open(path) as decoded:
            assert decoded.convert("RGBA").tobytes() == im.tobytes()
        save_contact([im.crop((i*192,j*208,(i+1)*192,(j+1)*208))
                      for j in range(11) for i in range(COUNTS[j])], output / f"{form}-contact.png")
    for strip, record in zip(inputs, records):
        frames = [strip.crop((i*192,0,(i+1)*192,208)) for i in range(record["frames"])]
        save_preview(frames, record["durationsMs"], output / f'{record["form"]}-{record["state"]}.gif')
    report = {"status": "STRUCTURAL_PASS", "spriteVersion": 2, "atlasSize": [1536,2288],
              "replacements": records, "untouched": ["both Look rows", "all other rows", "both transitions", "frozen source atlases"],
              "base": {form: {"path": str((BASE/f"{form}.webp").relative_to(ROOT)), "sha256": sha256(BASE/f"{form}.webp")} for form in originals},
              "outputSha256": {form: sha256(output/f"{form}.webp") for form in originals},
              "pixelPreservation": "Replaced cells exact approved RGBA; all other rows exact prior selected atlas; lossless WebP decode verified.",
              "inheritedAlpha": {form: {str(row): int(((np.array(im)[row*208:(row+1)*208,:,3]>0)&(np.array(im)[row*208:(row+1)*208,:,3]<255)).sum()) for row in range(11)} for form, im in atlases.items()},
              "warning": "Existing Gu Waiting/Running/Review semi-transparent pixels and both atlases' Idle slot 6 (unused by current six-frame runtime) preserved unchanged. This is a scoped integration validator, not a clean-atlas all-slot certification.",
              "appTest": "NOT_TESTED"}
    (output / "manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
