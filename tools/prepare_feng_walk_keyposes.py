"""Isolated references for Feng's four walking key poses; no runtime writes."""
from pathlib import Path
import hashlib
import json
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets/rework/v0.1.0/feng-walk-right-keyposes-2026-10-23"
ATLAS = ROOT / "assets/builds/feng/spritesheet.webp"
PROTECTED = [
    "assets/builds/gu/spritesheet.webp", "assets/builds/feng/spritesheet.webp",
    "assets/feng/idle.png", "standalone-app/asset-overrides.json",
    "assets/rework/v0.1.0/gu-drag-right-suspended-2026-10-21/revision-2/review-status.json",
    "assets/rework/v0.1.0/gu-drag-left-suspended-2026-10-22/review-status.json",
    "assets/rework/v0.1.0/feng-look-r6-2026-10-20/review-status.json",
    "assets/rework/v0.1.0/feng-failed-r3-2026-10-20/nod-revision/review-status.json",
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(output=OUT):
    if output.exists():
        raise FileExistsError("Do not overwrite references or a reviewed candidate")
    idle = Image.open(ATLAS).convert("RGBA").crop((0, 0, 192, 208))
    assert idle.getbbox() == (44, 4, 148, 204)
    output.mkdir(parents=True)
    idle.save(output / "canonical-idle.png")
    enlarged = idle.resize((768, 832), Image.Resampling.NEAREST)
    enlarged.save(output / "idle-reference-4x.png")
    target = Image.new("RGBA", (1536, 1664))
    for i in range(4):
        target.paste(enlarged, ((i % 2)*768, (i // 2)*832))
    target.save(output / "edit-target-four-idles.png")
    record = {
        "status": "SPEC_READY", "userApproval": "PENDING", "runtimeIntegrated": False,
        "scope": "feng-right-four-keyposes-only", "frameCount": 4, "cell": [192, 208],
        "baseline": 203, "registrationX": 96,
        "sourceOrder": ["N-contact", "N-support-F-passing", "F-contact", "F-support-N-passing"],
        "canonicalBbox": list(idle.getbbox()), "canonicalHeadReference": [64, 4, 113, 61],
        "sources": {p: sha(ROOT/p) for p in PROTECTED},
    }
    (output / "source-manifest.json").write_text(json.dumps(record, indent=2)+"\n")
    return record


if __name__ == "__main__":
    print(json.dumps(prepare(), indent=2))
