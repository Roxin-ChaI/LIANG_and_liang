"""Read approved pixels and prepare local edit references; never touch runtime."""
from pathlib import Path
import hashlib
import json
import sys

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build_animation_review import cell, save_contact, save_preview

OUT = ROOT / "assets/rework/v0.1.0/feng-failed-r3-2026-10-20"
FENG = ROOT / "assets/builds/feng/spritesheet.webp"
GU = ROOT / "assets/rework/v0.1.0/action-repair-2026-10-02/gu.webp"


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    idle = cell(Image.open(FENG).convert("RGBA"), 0, 0)
    refs = [cell(Image.open(GU).convert("RGBA"), 5, i) for i in range(8)]
    idle.save(OUT / "canonical-idle.png")
    save_contact(refs, OUT / "gu-motion-reference.png")
    save_preview(refs, [180] * 7 + [400], OUT / "gu-motion-reference.gif")
    # One editable upper-body reference: canonical pixels, no rejected art.
    idle.crop((52, 0, 124, 88)).resize((576, 704), Image.Resampling.NEAREST).save(
        OUT / "head-and-raised-hand-reference.png")
    idle.crop((124, 126, 150, 156)).resize((312, 360), Image.Resampling.NEAREST).save(
        OUT / "lower-hand-reference.png")
    # Four matching local edit targets in fixed cells; unchanged body excluded.
    board = Image.new("RGBA", (1024, 1024))
    crop = idle.crop((56, 0, 120, 80)).resize((384, 480), Image.Resampling.NEAREST)
    for i in range(4):
        board.paste(crop, (i % 2 * 512 + 64, i // 2 * 512 + 16))
    board.save(OUT / "upper-local-edit-target.png")
    manifest = {
        "status": "PREPARED_LOCAL_EDIT_INPUTS", "userApproval": "PENDING",
        "runtimeIntegrated": False, "frameCount": 8, "cell": [192, 208],
        "sources": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in (FENG, GU)},
    }
    (OUT / "source-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    print(json.dumps(prepare(), indent=2))
