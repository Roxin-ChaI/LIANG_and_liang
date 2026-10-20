"""Feng Look eye-only candidate: reuse coherent Idle art, no resampling."""
from pathlib import Path
import sys
import json
import hashlib
import math

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.repair_reviewed_actions import frame
from tools.build_animation_review import save_contact, save_preview

SOURCE = ROOT / "assets/builds/feng/spritesheet.webp"
OUT = ROOT / "assets/rework/v0.1.0/feng-look-r4-2026-10-06"

# Hand-tuned apertures inside the approved Idle eyelids and glasses.
# None of the lens rim, brow, skin contour or clothing belongs to this mask.
EYE_ROWS = {39: [(76, 82)], 40: [(77, 81)],
            38: [(91, 97)]}
RIGHT_BOTTOM = [(91, 39), (92, 39), (93, 39), (94, 39)]


def eye_mask():
    mask = np.zeros((208, 192), bool)
    for y, spans in EYE_ROWS.items():
        for left, right in spans:
            mask[y, left:right] = True
    for x, y in RIGHT_BOTTOM:
        mask[y, x] = True
    return mask


def look(base, angle):
    p = np.array(base)
    mask = eye_mask()
    # Reuse approved sclera, iris and pupil colors without interpolation.
    white = base.getpixel((77, 39))
    pupil = base.getpixel((78, 39))
    iris = base.getpixel((79, 39))
    p[mask] = white
    radians = math.radians(angle)
    dx = round(2 * math.sin(radians))
    down = math.cos(radians) < 0
    for cx, top in [(79, 39), (94, 38)]:
        y = top + int(down)
        x = cx + dx
        # The lower aperture tapers. Clip within the *eye*, never the figure.
        legal = np.flatnonzero(mask[y])
        legal = legal[(legal >= cx-3) & (legal <= cx+3)]
        x = max(int(legal.min()), min(int(legal.max())-1, x))
        p[y, x] = pupil
        p[y, x+1] = iris
    return Image.fromarray(p)


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / "review-status.json").exists():
        raise RuntimeError("Reviewed candidate locked")
    atlas = Image.open(SOURCE).convert("RGBA")
    original_idle = frame(atlas, 0, 0)
    base = original_idle.copy()
    removed = 0
    frames = [look(base, i*22.5) for i in range(16)]
    for i, im in enumerate(frames):
        im.save(OUT / f"{i+1:02d}.png")
    base.save(OUT / "coherent-idle-body.png")
    Image.fromarray(eye_mask().astype(np.uint8)*255).save(OUT / "eye-edit-mask.png")
    for row in (9, 10):
        strip = Image.new("RGBA", (1536, 208))
        for i in range(8):
            strip.paste(frames[(row-9)*8+i], (192*i, 0))
        strip.save(OUT / f"look-row-{row}.png")
    save_contact(frames, OUT / "contact.png")
    save_preview(frames, [180]*16, OUT / "preview.gif")
    save_preview(frames, [500]*16, OUT / "preview-slow.gif")
    save_preview(frames, [500]*16, OUT / "detail-preview.gif", display_size=(768, 832))
    comparisons = Image.new("RGB", (1152, 425), (64, 28, 65))
    draw = ImageDraw.Draw(comparisons)
    for col, (label, path) in enumerate([
        ("REJECTED R3", ROOT / "assets/rework/v0.1.0/feng-look-r3-2026-10-04/14.png"),
        ("APPROVED IDLE", None), ("R4 / LEFT", OUT / "13.png")]):
        im = Image.open(path).convert("RGBA") if path else original_idle
        for row, roi in enumerate([(40, 45, 148, 115), (62, 30, 114, 53)]):
            crop = im.crop(roi)
            scale = 3 if row == 0 else 6
            crop = crop.resize((crop.width*scale, crop.height*scale), Image.Resampling.NEAREST)
            comparisons.paste(crop, (col*384+10, row*260+35), crop.getchannel("A"))
            draw.text((col*384+10, row*260+8), label, fill="white")
    comparisons.save(OUT / "structural-comparison.png")
    details = Image.new("RGB", (896, 4*230), (64, 28, 65))
    draw = ImageDraw.Draw(details)
    for i, im in enumerate(frames):
        crop = im.crop((68, 32, 106, 45)).resize((152, 52), Image.Resampling.NEAREST)
        x, y = (i%4)*224, (i//4)*230
        details.paste(crop, (x, y+22), crop.getchannel("A"))
        draw.text((x+4, y+4), f"{i+1:02d} / {i*22.5:g}", fill="white")
        body = im.crop((40, 50, 148, 110)).resize((216, 120), Image.Resampling.NEAREST)
        details.paste(body, (x, y+95), body.getchannel("A"))
    details.save(OUT / "all-eyes-and-sleeves.png")
    p = np.array(base)
    report = {
        "status": "SELF_REVIEW_PENDING", "userApproval": "PENDING",
        "method": "Single coherent approved Idle body and head; only pupils inside explicit eye apertures change",
        "scopeChange": "Head silhouette remains fixed; Look expresses gaze direction only",
        "sourceSha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "runtimeIntegrated": False, "exteriorMattePixelsRemoved": removed,
        "eyeMaskPixels": int(eye_mask().sum()),
        "distinctPixelFrames": len({im.tobytes() for im in frames}),
        "frames": [{"frame": i+1, "direction": i*22.5,
                    "outsideEyeMaskPixelIdentical": bool(np.all(np.array(im)[~eye_mask()] == p[~eye_mask()])),
                    "bbox": im.getchannel("A").getbbox()}
                   for i, im in enumerate(frames)],
        "dynamicPlaybackObserved": "NOT_VERIFIED"
    }
    (OUT / "validation.json").write_text(json.dumps(report, indent=2)+"\n")
    (OUT / "index.html").write_text('''<!doctype html><meta charset="utf-8"><title>Feng Look R4</title>
<style>body{background:#26292f;color:#eee;font:16px system-ui;margin:24px}img{image-rendering:pixelated;max-width:100%}section{display:flex;gap:24px;flex-wrap:wrap}a{color:#9dd7ff}</style>
<h1>Feng Look R4 · 完整 Idle 身体，眼神方向候选</h1>
<p>手、手肘、袖口、领口与整套西装固定为同一张正式 Idle。头部轮廓固定，仅眼神改变。16 方向槽位中，相邻方向因眼睛像素空间有限可能相同。尚未用户批准，未接入 App。</p>
<section><div><h2>正常速度</h2><img src="preview.gif"></div><div><h2>慢速</h2><img src="preview-slow.gif"></div></section>
<h2>全部方向</h2><img src="contact.png"><h2>手肘、袖口、领口及眼睛对照</h2><img src="structural-comparison.png">
<h2>16 帧眼部与衣袖</h2><img src="all-eyes-and-sleeves.png"><p><a href="validation.json">验证报告</a></p>''', encoding="utf-8")
    return frames


def diagnostics():
    OUT.mkdir(parents=True, exist_ok=True)
    atlas = Image.open(SOURCE).convert("RGBA")
    samples = [frame(atlas, 0, 0), frame(atlas, 9, 0), frame(atlas, 9, 4),
               frame(atlas, 10, 0), frame(atlas, 10, 4)]
    names = ["IDLE", "UP", "RIGHT", "DOWN", "LEFT"]
    board = Image.new("RGB", (600 * 5, 720), (65, 30, 65))
    draw = ImageDraw.Draw(board)
    for i, (sample, name) in enumerate(zip(samples, names)):
        enlarged = sample.crop((35, 0, 155, 138)).resize((600, 690), Image.Resampling.NEAREST)
        board.paste(enlarged, (i*600, 30), enlarged.getchannel("A"))
        draw.text((i*600+4, 4), name, fill="white")
        for y in range(40, 131, 10):
            draw.line((i*600, 30+y*5, (i+1)*600-1, 30+y*5), fill=(160, 75, 110))
            draw.text((i*600+3, 30+y*5), str(y), fill="white")
    board.save(OUT / "source-diagnosis.png")
    idle = samples[0]
    eye = idle.crop((67, 33, 115, 49)).resize((960, 320), Image.Resampling.NEAREST)
    eye_board = Image.new("RGB", (1000, 370), (65, 30, 65))
    eye_board.paste(eye, (40, 30), eye.getchannel("A"))
    draw = ImageDraw.Draw(eye_board)
    for x in range(67, 115):
        draw.text((40+(x-67)*20, 12), str(x), fill="white")
    for y in range(33, 49):
        draw.text((3, 30+(y-33)*20), str(y), fill="white")
    eye_board.save(OUT / "idle-eye-map.png")


if __name__ == "__main__":
    diagnostics()
    build()
