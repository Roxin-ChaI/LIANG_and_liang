"""Normalize a local generated body; preserve the original Gu head pixels.

Art comes from the built-in image editor. This script performs disclosed
nearest-neighbor normalization, palette restriction, packing and QA only.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.prepare_gu_drag_suspended import OUT, BODY_BOX, assert_unapproved, sha
from tools.build_animation_review import save_preview, save_contact
from tools.finish_feng_look_r6 import components

R2 = OUT / "revision-2"


def normalize_r2():
    assert_unapproved(R2)
    original = np.array(Image.open(OUT / "canonical-idle.png").convert("RGBA"))
    raw = Image.open(R2 / "source-body-edit.png").convert("RGBA")
    crop = np.array(raw.resize((96,132), Image.Resampling.NEAREST))
    crop[crop[:,:,3] < 128] = 0
    crop[crop[:,:,3] >= 128,3] = 255
    # Only the generated knee/ankle/shoe edit survives. No AI-generated head,
    # neck, torso, arm or hand pixels enter the sprite.
    lower = original[160:]
    palette = np.unique(lower[lower[:,:,3] > 0,:3],axis=0).astype(np.int32)
    visible = crop[:,:,3] > 0
    for color in np.unique(crop[visible,:3],axis=0):
        match = palette[np.square(palette-color.astype(np.int32)).sum(1).argmin()]
        crop[visible & np.all(crop[:,:,:3] == color,axis=2),:3] = match
    base = original.copy()
    base[160:] = 0
    base[160:,40:136] = crop[84:]
    base[base[:,:,3] == 0] = 0
    pose = Image.fromarray(base)
    pose.save(R2 / "suspended-base.png")
    save_contact([Image.fromarray(original),pose],R2 / "base-vs-idle.png",columns=2)
    pair = Image.new("RGB",(768,832),(35,38,44))
    for i, frame in enumerate([Image.fromarray(original),pose]):
        p=frame.resize((384,416),Image.Resampling.NEAREST)
        pair.paste(p,(i*384,0),p.getchannel("A"))
        p=frame.crop((56,140,128,208)).resize((360,340),Image.Resampling.NEAREST)
        pair.paste(p,(i*384,440),p.getchannel("A"))
    pair.save(R2 / "base-detail.png")
    print(json.dumps({"bbox":pose.getbbox(),"components":len(components(pose)),
                     "lockedTop160":bool(np.array_equal(base[:160],original[:160]))}))


def normalize():
    assert_unapproved()
    idle = Image.open(OUT / "canonical-idle.png").convert("RGBA")
    raw = Image.open(OUT / "source-body-edit.png").convert("RGBA")
    # Use the fixed reference crop, never fit or stretch to a foreground bbox.
    size = (BODY_BOX[2] - BODY_BOX[0], BODY_BOX[3] - BODY_BOX[1])
    crop = np.array(raw.resize(size, Image.Resampling.NEAREST))
    crop[crop[:, :, 3] < 128] = 0
    crop[crop[:, :, 3] >= 128, 3] = 255
    original = np.array(idle)
    body = original[BODY_BOX[1]:]
    palette = np.unique(body[body[:, :, 3] > 0, :3], axis=0).astype(np.int32)
    visible = crop[:, :, 3] > 0
    for color in np.unique(crop[visible, :3], axis=0):
        match = palette[np.square(palette - color.astype(np.int32)).sum(1).argmin()]
        crop[visible & np.all(crop[:, :, :3] == color, axis=2), :3] = match
    result = np.zeros_like(original)
    result[BODY_BOX[1]:BODY_BOX[3], BODY_BOX[0]:BODY_BOX[2]] = crop
    # Full head plus original neck/upper shoulder pixels, no head transplant
    # transform and no adjustment of head size or registration.
    result[:88] = original[:88]
    result[result[:, :, 3] == 0] = 0
    pose = Image.fromarray(result)
    pose.save(OUT / "suspended-base.png")
    pose.resize((768,832), Image.Resampling.NEAREST).save(OUT / "suspended-base-4x.png")
    save_contact([idle,pose], OUT / "base-vs-idle.png", columns=2)
    comparison = Image.new("RGB",(768,832),(35,38,44))
    for i, frame in enumerate([idle,pose]):
        p = frame.resize((384,416),Image.Resampling.NEAREST)
        comparison.paste(p,(i*384,0),p.getchannel("A"))
        detail=frame.crop((56,64,136,160)).resize((320,384),Image.Resampling.NEAREST)
        comparison.paste(detail,(i*384+32,440),detail.getchannel("A"))
    comparison.save(OUT / "base-detail.png")
    print(json.dumps({"bbox":pose.getbbox(),"components":len(components(pose)),
                      "sourceSize":raw.size,"normalizationCanvas":size}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["normalize", "normalize-r2"])
    args = parser.parse_args()
    {"normalize":normalize, "normalize-r2":normalize_r2}[args.command]()
