"""Prepare canonical references for the isolated Gu right-drag art review."""
from pathlib import Path
import hashlib
import json
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build_animation_review import cell

OUT = ROOT / "assets/rework/v0.1.0/gu-drag-right-suspended-2026-10-21"
GU = ROOT / "assets/builds/gu/spritesheet.webp"
FENG = ROOT / "assets/builds/feng/spritesheet.webp"
BODY_BOX = (40, 76, 136, 208)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_unapproved(folder=OUT):
    record = folder / "review-status.json"
    if record.exists() and json.loads(record.read_text()).get("generatorLocked"):
        raise RuntimeError("Approved Gu drag candidate is frozen; create a new revision")


def prepare():
    assert_unapproved()
    OUT.mkdir(parents=True, exist_ok=True)
    idle = cell(Image.open(GU).convert("RGBA"), 0, 0)
    idle.save(OUT / "canonical-idle.png")
    idle.resize((768, 832), Image.Resampling.NEAREST).save(OUT / "idle-reference-4x.png")
    idle.crop(BODY_BOX).resize((576, 792), Image.Resampling.NEAREST).save(
        OUT / "body-edit-target-6x.png")
    record = {
        "status": "SPEC_READY", "userApproval": "PENDING", "runtimeIntegrated": False,
        "scope": "gu-running-right-only", "frameCount": 8, "cell": [192, 208],
        "bodyEditBox": list(BODY_BOX), "canonicalBbox": list(idle.getbbox()),
        "baseline": 203, "motion": "suspended-by-nape-passive-right-drag",
        "sources": {str(p.relative_to(ROOT)): sha(p) for p in (
            GU, FENG, ROOT / "assets/gu/idle.png", ROOT / "standalone-app/asset-overrides.json")},
        "deferred": ["feng-look-intermediates", "gu-drag-left", "feng-drag-right", "feng-drag-left"],
    }
    (OUT / "source-manifest.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


if __name__ == "__main__":
    print(json.dumps(prepare(), indent=2))
