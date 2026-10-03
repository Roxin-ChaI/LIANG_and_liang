#!/usr/bin/env python3
"""Derive narrowly scoped action repairs from existing RGBA art; no generation."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build_animation_review import save_preview, save_contact

OUTPUT = ROOT / "assets/rework/v0.1.0/action-repair-2026-10-02"
COUNTS = {0: 6, 1: 8, 2: 8, 3: 4, 4: 5, 5: 8, 6: 6, 7: 6, 8: 6, 9: 8, 10: 8}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frame(atlas, row, index):
    return atlas.crop((index * 192, row * 208, (index + 1) * 192, (row + 1) * 208))


def skin_mask(image):
    p = np.asarray(image).astype(np.int16)
    return (p[:, :, 3] > 0) & (p[:, :, 0] > 110) & (p[:, :, 0] > p[:, :, 1] + 10) & (p[:, :, 1] > p[:, :, 2] + 8)


def clean_neutral_fringe(image, form):
    """Only neutral bright pixels touching transparency; protect hand/cuff zones."""
    result = image.copy()
    skin = skin_mask(image)
    skin[:85 if form == "feng" else 96] = False
    hand_zone = np.asarray(Image.fromarray(skin.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(9))) > 0
    removed = np.zeros((208, 192), dtype=bool)
    for _ in range(2):
        p = np.array(result)
        alpha = p[:, :, 3] > 0
        inner = np.asarray(Image.fromarray(alpha.astype(np.uint8) * 255).filter(ImageFilter.MinFilter(3))) > 0
        rgb = p[:, :, :3].astype(np.int16)
        neutral = (rgb.max(axis=2) - rgb.min(axis=2) <= 25) & (rgb.min(axis=2) >= 85)
        cut = alpha & ~inner & neutral & ~hand_zone
        p[cut] = 0
        removed |= cut
        result = Image.fromarray(p)
    return result, Image.fromarray(removed.astype(np.uint8) * 255)


def head_mask(image, form):
    """Follow the face/neck silhouette instead of cutting through the shoulders."""
    cutoff, last = (70, 94) if form == "gu" else (45, 74)
    mask = np.zeros((208, 192), dtype=np.uint8)
    mask[:cutoff] = 255
    skin = skin_mask(image)
    for y in range(cutoff, last):
        xs = np.flatnonzero(skin[y, 45:148]) + 45
        if len(xs):
            mask[y, max(0, int(xs.min()) - 1):min(192, int(xs.max()) + 2)] = 255
    return Image.fromarray(mask)


def join_look_head(image, donor, form):
    # Remove the donor's head completely, retain its coherent collar/shoulders,
    # then copy the direction-specific head at the original integer coordinates.
    body = donor.copy()
    blank = Image.new("RGBA", (192, 208))
    body.paste(blank, (0, 0), head_mask(donor, form))
    body.paste(image, (0, 0), head_mask(image, form))
    return body


def difference(before, after):
    a, b = np.asarray(before), np.asarray(after)
    changed = np.any(a != b, axis=2)
    mask = np.zeros_like(a)
    mask[changed] = [255, 70, 150, 255]
    return Image.fromarray(mask), int(changed.sum())


def pair_sheet(before, after, output, crop=(0, 0, 192, 208), scale=2):
    width, height = (crop[2] - crop[0]) * scale, (crop[3] - crop[1]) * scale
    sheet = Image.new("RGB", (width * 3, (height + 22) * len(before)), (42, 34, 54))
    draw = ImageDraw.Draw(sheet)
    for i, (a, b) in enumerate(zip(before, after)):
        d, _ = difference(a, b)
        for column, im in enumerate((a, b, d)):
            x, y = column * width, i * (height + 22)
            enlarged = im.crop(crop).resize((width, height), Image.Resampling.NEAREST)
            sheet.paste(enlarged, (x, y + 22), enlarged.getchannel("A"))
            draw.text((x + 4, y + 4), f"{i + 1:02d} {('BEFORE','AFTER','DIFF')[column]}", fill="white")
    sheet.save(output)


def build(output=OUTPUT):
    output.mkdir(parents=True, exist_ok=True)
    qa = output / "qa"
    qa.mkdir(exist_ok=True)
    sources = [ROOT / f"assets/builds/{form}/spritesheet.webp" for form in ("gu", "feng")]
    frozen = {str(path.relative_to(ROOT)): digest(path) for path in sources}
    report = {"sources": frozen, "operations": [], "visualStatus": "REQUIRES_REVIEW"}
    overrides = {}
    for form, original_path in zip(("gu", "feng"), sources):
        original = Image.open(original_path).convert("RGBA")
        # This previously approved five-row correction supplies the same baseline
        # used by the selected eye-repair strips.
        base = ROOT / "assets/rework/v0.1.0/gu/spritesheet.webp" if form == "gu" else original_path
        repaired = Image.open(base).convert("RGBA")
        if form == "gu":
            for name, row in (("failed", 5), ("waiting", 6)):
                source = ROOT / f"assets/rework/v0.1.0/gu-eye-repair-2026-10-01/{name}.png"
                strip = Image.open(source).convert("RGBA")
                repaired.paste(strip, (0, row * 208))
                report["operations"].append({"form": form, "state": name, "operation": "selected eye-repair strip copied exactly", "sha256": digest(source)})
        rows = (1, 2, 3) if form == "feng" else (3,)
        for row in rows:
            before, after = [], []
            for index in range(COUNTS[row]):
                a = frame(repaired, row, index)
                b, mask = clean_neutral_fringe(a, form)
                repaired.paste(b, (index * 192, row * 208))
                mask.save(qa / f"{form}-row{row}-{index+1:02d}-fringe-mask.png")
                before.append(a); after.append(b)
                report["operations"].append({"form": form, "row": row, "frame": index + 1,
                    "removedBoundaryPixels": int((np.asarray(mask) > 0).sum()), "handCuffProtection": True})
            pair_sheet(before, after, qa / f"{form}-row{row}-edge-comparison.png", scale=2)
        donor = frame(repaired, 9, 0)
        before, after = [], []
        for direction in range(16):
            row, index = 9 + direction // 8, direction % 8
            a = frame(repaired, row, index)
            b = join_look_head(a, donor, form)
            repaired.paste(b, (index * 192, row * 208))
            d, count = difference(a, b)
            d.save(qa / f"{form}-look-{direction:02d}-difference.png")
            before.append(a); after.append(b)
            cutoff = 70 if form == "gu" else 45
            assert a.crop((0, 0, 192, cutoff)).tobytes() == b.crop((0, 0, 192, cutoff)).tobytes()
            report["operations"].append({"form": form, "direction": direction * 22.5,
                                         "lookChangedPixels": count, "headUpperPixelsUnchanged": True})
        pair_sheet(before, after, qa / f"{form}-look-shoulder-comparison.png", crop=(35, 38, 155, 110), scale=3)
        target = output / f"{form}.webp"
        repaired.save(target, lossless=True, exact=True, method=6)
        assert Image.open(target).convert("RGBA").tobytes() == repaired.tobytes()
        overrides[f"assets/builds/{form}/spritesheet.webp"] = str(target.relative_to(ROOT))
        for row, name in ((1, "running-right"), (2, "running-left"), (3, "waving"), (5, "failed"), (6, "waiting")):
            count = COUNTS[row]
            old = [frame(original, row, index) for index in range(count)]
            new = [frame(repaired, row, index) for index in range(count)]
            pairs = []
            for a, b in zip(old, new):
                pair = Image.new("RGBA", (384, 208)); pair.paste(a, (0, 0)); pair.paste(b, (192, 0)); pairs.append(pair)
            lengths = [120] * count if row in (1, 2) else [150] * count
            save_preview(pairs, lengths, qa / f"{form}-{name}-before-after.gif", display_size=(768, 416))
            save_contact(new, qa / f"{form}-{name}-frames.png")
        save_preview(after, [180] * 16, qa / f"{form}-look-after.gif")
        save_contact(after, qa / f"{form}-look-frames.png")
    manifest = []
    for direction, count in (("gu_to_feng", 10), ("feng_to_gu", 8)):
        for i in range(count):
            logical = f"assets/transform-overlay/{direction}/{direction}_{i+1:02d}.png"
            if direction == "gu_to_feng":
                source = ROOT / f"assets/rework/v0.1.0/transition-full/gu-to-feng-retry/frames/gu_to_feng_{i:02d}.png"
                image = Image.open(source).convert("RGBA")
                assert image.size == (192, 208)
                padded = Image.new("RGBA", (224, 240))
                padded.paste(image, (16, 18))
                target = output / "gu_to_feng" / f"gu_to_feng_{i+1:02d}.png"
                target.parent.mkdir(exist_ok=True)
                padded.save(target)
                assert padded.crop((16, 18, 208, 226)).tobytes() == image.tobytes()
                overrides[logical] = str(target.relative_to(ROOT))
            else:
                target = ROOT / logical
            manifest.append(f"{digest(target)}  {logical}")
    manifest_file = output / "transform-overlay.sha256"
    manifest_file.write_text("\n".join(manifest) + "\n")
    overrides["assets/transform-overlay.sha256"] = str(manifest_file.relative_to(ROOT))
    report["forwardTransition"] = {"source": "historical trial 2", "count": 10,
        "operation": "exact RGBA copy at (16,18); no resize; logical registration x96 baseline203"}
    report["sourceHashesUnchanged"] = all(digest(ROOT / key) == value for key, value in frozen.items())
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    (output / "asset-overrides.json").write_text(json.dumps(overrides, indent=2) + "\n")
    return report


if __name__ == "__main__":
    result = build()
    print(json.dumps({"output": str(OUTPUT), "sourceHashesUnchanged": result["sourceHashesUnchanged"]}))
