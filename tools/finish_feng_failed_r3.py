"""Compose local generated edits over unchanged Idle; produce review-only QA."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.prepare_feng_failed_r3 import OUT, FENG
from tools.build_animation_review import save_contact, save_preview, cell
from tools.finish_feng_look_r6 import components

DURATIONS = [280, 140, 160, 160, 260, 180, 160, 400]
POSE_ORDER = [None, 0, 1, 2, 2, 3, 0, None]


def masks(idle):
    p = np.array(idle)
    head = np.zeros((208, 192), bool)
    head[:48, 60:119] = True
    for y, (left, right) in enumerate([
        (74,108),(75,107),(76,106),(77,105),(78,104),(79,103),
        (80,103),(81,103),(82,102),(83,101),(83,100),(83,99),(82,99)], 48):
        head[y, left:right] = True
    raised = np.zeros_like(head)
    # Skin outline of the existing raised palm; wrist/cuff rows 77+ frozen.
    for y, (left, right) in enumerate([
        (80,94),(79,94),(78,93),(78,93),(77,93),(77,93),
        (77,93),(76,93),(76,92),(76,91),(75,91),(75,90),
        (75,90),(75,89),(74,89),(75,88),(75,87)], 60):
        raised[y, left:right] = True
    lower = np.zeros_like(head)
    lower[136:150, 129:144] = True
    # Canonical suit/collar pixels are always protected. Skin and black outline
    # may change; pale shirt/cuff and blue cloth may not.
    rgb = p[:, :, :3].astype(int)
    cloth = (rgb[:, :, 2] > rgb[:, :, 0] + 8) | (
        (rgb.min(2) > 145) & (rgb.max(2) - rgb.min(2) < 45))
    cloth[:48] = False
    for mask in (head, raised, lower):
        mask[cloth] = False
    return head, raised, lower


def palette_match(pixels, reference):
    p = pixels.copy()
    p[p[:, :, 3] < 128] = 0
    p[p[:, :, 3] >= 128, 3] = 255
    palette = np.unique(reference[reference[:, :, 3] > 0, :3], axis=0).astype(np.int32)
    visible = p[:, :, 3] > 0
    for color in np.unique(p[visible, :3], axis=0):
        match = palette[np.square(palette - color.astype(np.int32)).sum(1).argmin()]
        p[visible & np.all(p[:, :, :3] == color, axis=2), :3] = match
    return p


def local_edits(idle, source_path=None):
    raw = Image.open(source_path or OUT / "source-upper-edit.png").convert("RGBA")
    source = np.array(idle)
    results = []
    for i in range(4):
        halfx, halfy = raw.width // 2, raw.height // 2
        tile = raw.crop((i % 2 * halfx, i // 2 * halfy,
                         (i % 2 + 1) * halfx, (i // 2 + 1) * halfy))
        tile = tile.resize((512, 512), Image.Resampling.NEAREST)
        crop = tile.crop((64, 16, 448, 496)).resize((64, 80), Image.Resampling.NEAREST)
        layer = Image.new("RGBA", (192, 208))
        layer.paste(crop, (56, 0))
        results.append(palette_match(np.array(layer), source[:80]))
    return results


def build(output=OUT, upper_source=None, lock_head_silhouette=False):
    output.mkdir(parents=True, exist_ok=True)
    idle = cell(Image.open(FENG).convert("RGBA"), 0, 0)
    p = np.array(idle)
    head, raised, lower = masks(idle)
    edits = local_edits(idle, upper_source)
    # Same palm pixels throughout the hold: no independently moving AI hands.
    fist = local_edits(idle)[0] if upper_source else edits[0]
    small = Image.open(OUT / "source-lower-hand.png").convert("RGBA")
    small = small.resize((26, 30), Image.Resampling.NEAREST)
    layer = Image.new("RGBA", (192, 208)); layer.paste(small, (124, 126))
    lower_fist = palette_match(np.array(layer), p[130:151])
    editable = head | raised | lower
    Image.fromarray(editable.astype(np.uint8) * 255).save(output / "editable-mask.png")
    Image.fromarray((~editable).astype(np.uint8) * 255).save(output / "locked-mask.png")
    frames = []
    for i, pose in enumerate(POSE_ORDER):
        q = p.copy()
        if pose is not None:
            q[head] = edits[pose][head]
            if lock_head_silhouette:
                # Preserve the exact canonical head footprint. Empty generated
                # edge samples fall back to Idle, never a stretched/shifted head.
                edge = head & ((p[:, :, 3] == 0) | (edits[pose][:, :, 3] == 0))
                q[edge] = p[edge]
            q[raised] = fist[raised]
            q[lower] = lower_fist[lower]
        q[q[:, :, 3] == 0] = 0
        im = Image.fromarray(q)
        im.save(output / f"failed-{i+1:02d}.png")
        frames.append(im)
    strip = Image.new("RGBA", (1536, 208))
    for i, im in enumerate(frames): strip.paste(im, (192*i, 0))
    strip.save(output / "feng-failed.png")
    save_contact(frames, output / "contact.png")
    save_preview(frames, DURATIONS, output / "preview.gif")
    save_preview(frames, [600]*8, output / "preview-slow.gif")
    details = [im.crop((56, 0, 120, 88)) for im in frames]
    save_preview(details, DURATIONS, output / "head-hand-preview.gif", display_size=(384,528))
    board = Image.new("RGB", (8*256, 376), (45,39,48))
    draw = ImageDraw.Draw(board)
    for i, im in enumerate(details):
        im = im.resize((256,352), Image.Resampling.NEAREST)
        board.paste(im, (i*256,24), im.getchannel("A"))
        draw.text((i*256+6,5), f"{i+1:02d}", fill="white")
    board.save(output / "head-hand-contact.png")
    comparisons = []
    for im in frames:
        pair = Image.new("RGBA", (384,232))
        pair.paste(idle,(0,24)); pair.paste(im,(192,24))
        d=ImageDraw.Draw(pair);d.text((6,4),"FENG IDLE / LOCKED",fill="white")
        d.text((198,4),"FAILED / CANDIDATE",fill="white")
        comparisons.append(pair)
    save_preview(comparisons,DURATIONS,output/"idle-comparison.gif",display_size=(768,464))
    report = {
        "status": "SELF_REVIEW_REJECTED_NOD_TOO_WEAK", "userApproval": "PENDING",
        "selfReview": {
            "bodySeams": "No visible new elbow/cuff/lapel tearing in native and 4x contact sheets",
            "motion": "Predominantly eyelid motion; downward pitch is not clear enough against Gu reference",
            "decision": "Do not integrate; revise only local head motion",
        },
        "runtimeIntegrated": False, "imagegenUsed": True,
        "normalization": "shared fixed input-cell coordinates, nearest-neighbor; no body resampling",
        "poseOrder": POSE_ORDER, "durationsMs": DURATIONS,
        "hold": "Frames 4/5 intentionally repeat for the closed-eye pause; 1/8 exact Idle",
        "sourceAtlasSha256": hashlib.sha256(FENG.read_bytes()).hexdigest(), "frames": [],
    }
    for i, im in enumerate(frames):
        q = np.array(im); changed = np.any(q != p, axis=2)
        diff = np.zeros_like(q); diff[changed] = [255,70,150,255]
        Image.fromarray(diff).save(output / f"diff-{i+1:02d}.png")
        b=im.getbbox()
        checks={
            "lockedPixelsIdentical": bool(np.array_equal(q[~editable],p[~editable])),
            "baseline203": b[3]-1 == 203, "fullFigureBbox": b == idle.getbbox(),
            "rgba192x208": im.size==(192,208) and im.mode=="RGBA",
            "binaryAlpha": set(np.unique(q[:,:,3]))=={0,255},
            "transparentRGBZero": not bool(q[q[:,:,3]==0,:3].any()),
            "oneConnectedFigure": len(components(im))==1,
            "cuffsWristsAndElbowsFrozen": bool(np.array_equal(q[77:130],p[77:130])),
        }
        report["frames"].append({"frame":i+1,"bbox":b,"changedPixels":int(changed.sum()),"checks":checks})
    report["structuralChecksPassed"]=all(all(f["checks"].values()) for f in report["frames"])
    report["headSilhouetteLocked"] = lock_head_silhouette
    report["upperSource"] = str(upper_source or OUT / "source-upper-edit.png")
    (output/"validation.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
