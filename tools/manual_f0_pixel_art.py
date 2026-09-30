"""Construct a transition-only Feng pose from approved native pixels.

This is a deliberately small, inspectable pixel-art edit recipe, not an
image-generation or resampling pipeline. It never writes to an approved source.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

from tools.audit_b_endpoint_compatibility import FENG_ATLAS, FENG_ATLAS_SHA, KB2, KB2_SHA
from tools.f0_transition_endpoint_spec import OUT, specification
from tools.prepare_transition_animation_candidate import digest
from tools.transition_bridge_spec import landmark

DEST = OUT / "manual-pixel-art"
CELL = (192, 208)
REVIEW_ROW, REVIEW_FRAME = 8, 4


def _native(image: Image.Image) -> Image.Image:
    image = image.convert("RGBA")
    if image.size != CELL or set(image.getchannel("A").get_flattened_data()) != {0, 255}:
        raise ValueError("native binary-alpha Feng donor required")
    return image


def donor() -> Image.Image:
    specification()
    if digest(FENG_ATLAS) != FENG_ATLAS_SHA or digest(KB2) != KB2_SHA:
        raise ValueError("approved source changed")
    with Image.open(FENG_ATLAS) as source:
        frame = source.crop((REVIEW_FRAME * 192, REVIEW_ROW * 208,
                             (REVIEW_FRAME + 1) * 192, (REVIEW_ROW + 1) * 208))
    return _native(frame)


def construct() -> tuple[Image.Image, dict]:
    """Copy approved face; lower both arms; locally draw a narrower stance.

    The right lower torso/arm is the untouched approved Review 8/4 pixel
    donor. Its left counterpart is manually registered pixel-by-pixel against
    the vertical suit seam. Below the belt, the two legs are moved *inward*
    by integer offsets rising gradually to six pixels at the soles. This
    changes pose, not scale: every moved opaque pixel retains its RGBA bytes.
    """
    source = donor()
    out = Image.new("RGBA", CELL, (0, 0, 0, 0))
    src, dst = source.load(), out.load()
    counts = {"approved_head_pixels": 0, "approved_right_side_pixels": 0,
              "mirrored_left_suit_pixels": 0, "integer_leg_repositions": 0,
              "manual_seam_pixels": 0}

    # True Feng face/hair/glasses, without a hand against the chin. No change
    # to skull coordinates, palette or individual face pixels.
    for y in range(0, 65):
        for x in range(192):
            dst[x, y] = src[x, y]
            if src[x, y][3]:
                counts["approved_head_pixels"] += 1

    # Hand-authored part placement: use the approved *low* right arm for the
    # left as well, preserving the donor's jacket shading and fist shape.
    # Original Review 8/4 left hand across chest is intentionally not copied.
    for y in range(65, 115):
        for x in range(96, 192):
            pixel = src[x, y]
            dst[x, y] = pixel
            dst[191 - x, y] = pixel
            if pixel[3]:
                counts["approved_right_side_pixels"] += 1
                counts["mirrored_left_suit_pixels"] += 1

    # Do not scale/warp a full body. Shift each lower leg by a bounded integer
    # number of native pixels to put F0 between KB2 and the broad Feng Idle.
    for y in range(115, 204):
        inward = min(6, max(0, (y - 115) * 6 // 88))
        for x in range(96, 192):
            pixel = src[x, y]
            if not pixel[3]:
                continue
            nx = x - inward
            dst[nx, y] = pixel
            dst[191 - nx, y] = pixel
            counts["integer_leg_repositions"] += 2

    # At the waist-to-leg seam the source's fine black outlines leave a
    # one-pixel notch after the first integer inward step. Repair it explicitly
    # using adjacent approved pants colors, never interpolating a new color.
    for x, y, from_x, from_y in ((95, 130, 96, 130), (96, 130, 97, 130)):
        if dst[x, y][3] == 0 and src[from_x, from_y][3]:
            dst[x, y] = src[from_x, from_y]
            counts["manual_seam_pixels"] += 1

    # No hidden RGB on transparent texels; preserve exact hard-edged alpha.
    for y in range(208):
        for x in range(192):
            if dst[x, y][3] == 0:
                dst[x, y] = (0, 0, 0, 0)
    report = {
        "method": "manual native-pixel placement; approved Feng Review row 8 frame 4",
        "donorAtlasSha256": digest(FENG_ATLAS),
        "donorCellRgbaSha256": hashlib.sha256(source.tobytes()).hexdigest(),
        "frozenKB2Sha256": digest(KB2),
        "head": "source exact pixels in y=0..64",
        "torsoAndArms": "source right half copied in y=65..114; low right arm reflected to left around seam x=95.5",
        "legs": "source lower-right pixels reflected to left; each leg moved inward by an integer 0..6 px over y=115..203",
        "manualSeam": "at most two explicit waist pixels from neighboring approved source pixels",
        "globalScaling": False, "interpolation": False, "aiImageGeneration": False,
        "counts": counts,
        "landmarks": landmark(out, [64, 4, 114, 59], approximate=True),
    }
    return out, report


def _sheet(kb2: Image.Image, f0: Image.Image, b: Image.Image) -> Image.Image:
    sheet = Image.new("RGBA", (3 * 192, 230), (28, 28, 32, 255))
    draw = ImageDraw.Draw(sheet)
    for i, (name, frame) in enumerate((("KB2", kb2), ("F0 manual draft", f0), ("B / Feng Idle", b))):
        x = i * 192
        draw.text((x + 4, 3), name, fill="white")
        sheet.alpha_composite(frame, (x, 20))
    return sheet


def write(output: Path = DEST, *, refresh_own_draft: bool = False) -> dict:
    if output.exists() and not (refresh_own_draft and (output / "provenance.json").exists()):
        raise ValueError("refuse to overwrite non-draft F0 evidence")
    f0, report = construct()
    with Image.open(KB2) as source:
        kb2 = source.copy()
    with Image.open(FENG_ATLAS) as source:
        b = source.crop((0, 0, 192, 208))
    output.mkdir(parents=True, exist_ok=refresh_own_draft)
    f0.save(output / "F0.png")
    _sheet(kb2, f0, b).save(output / "contact-sheet.png")
    overlay = Image.blend(kb2, f0, 0.5)
    overlay.save(output / "KB2-F0-alpha-overlay.png")
    delta = Image.new("RGBA", CELL, (0, 0, 0, 0))
    p = delta.load()
    for y in range(208):
        for x in range(192):
            if kb2.getpixel((x, y)) != f0.getpixel((x, y)):
                p[x, y] = (255, 64, 64, 255)
    delta.save(output / "KB2-F0-difference-mask.png")
    report["outputSha256"] = digest(output / "F0.png")
    report["outputRgbaSha256"] = hashlib.sha256(f0.tobytes()).hexdigest()
    (output / "provenance.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-own-draft", action="store_true")
    args = parser.parse_args()
    print(write(refresh_own_draft=args.refresh_own_draft)["outputSha256"])
