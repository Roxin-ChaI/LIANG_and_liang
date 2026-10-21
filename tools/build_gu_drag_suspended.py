"""Normalize a local generated body; preserve the original Gu head pixels.

Art comes from the built-in image editor. This script performs disclosed
nearest-neighbor normalization, palette restriction, packing and QA only.
"""
import argparse
import math
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
DURATIONS = [120] * 8


def row_offsets(frame):
    """Small suspended displacement, continuous through torso/arms/legs.

    Whole scanlines move as units. No limb is split on an arbitrary x boundary;
    no color or opacity interpolation, no deleted/duplicated source pixels.
    Head/neck above 88 stay fixed. The second phase term delays the body return
    relative to the feet, so the return path is not a reverse copy of five poses.
    """
    phase = 2 * math.pi * frame / 8
    t = np.clip((np.arange(208)-88)/105, 0, 1)
    return np.rint(-10*t - 4*t*math.sin(phase)
                   + 1.5*np.sin(np.pi*t)*math.cos(phase)).astype(int)


def sway(base, frame):
    source = np.array(base)
    result = np.zeros_like(source)
    for y, dx in enumerate(row_offsets(frame)):
        occupied = np.where(source[y,:,3] > 0)[0]
        if len(occupied) and (occupied.min()+dx < 0 or occupied.max()+dx >=192):
            raise ValueError("Motion would clip a source pixel")
        # Each scanline is a bijective integer translation within this canvas.
        if dx < 0:
            result[y,:dx] = source[y,-dx:]
        elif dx > 0:
            result[y,dx:] = source[y,:-dx]
        else:
            result[y] = source[y]
    return Image.fromarray(result)


def animate():
    assert_unapproved(R2)
    self_review = json.loads((R2/"base-self-review.json").read_text())
    if self_review["status"] != "BASE_SELF_REVIEW_PASSED_FOR_MOTION_STUDY":
        raise RuntimeError("Body draft must pass self-review before animation")
    idle = Image.open(OUT/"canonical-idle.png").convert("RGBA")
    base = Image.open(R2/"suspended-base.png").convert("RGBA")
    original = np.array(idle)
    source = np.array(base)
    frames = [sway(base,i) for i in range(8)]
    sheet=Image.new("RGBA",(1536,208))
    reports=[]
    for i, frame in enumerate(frames):
        frame.save(R2/f"right-{i+1:02d}.png")
        sheet.paste(frame,(192*i,0))
        q=np.array(frame);bbox=frame.getbbox()
        offsets=row_offsets(i)
        checks={
            "rgba192x208":frame.mode=="RGBA" and frame.size==(192,208),
            "headAndNeckByteIdentical":bool(np.array_equal(q[:88],original[:88])),
            "binaryAlpha":set(np.unique(q[:,:,3]))=={0,255},
            "transparentRgbZero":not bool(q[q[:,:,3]==0,:3].any()),
            "singleConnectedFigure":len(components(frame))==1,
            "marginAtLeast4":bbox[0]>=4 and bbox[1]>=4 and bbox[2]<=188 and bbox[3]<=204,
            "feetAirborne":bbox[3]-1==193,
            "noPixelLoss":int((q[:,:,3]>0).sum())==int((source[:,:,3]>0).sum()),
            "noRowTear":int(np.abs(np.diff(offsets)).max())<=1,
        }
        reports.append({"frame":i+1,"bbox":list(bbox),"lowestShoeY":bbox[3]-1,
                        "neckDx":int(offsets[88]),"waistDx":int(offsets[130]),
                        "handsDx":int(offsets[150]),"shoesDx":int(offsets[193]),
                        "checks":checks})
    sheet.save(R2/"gu-running-right.png")
    save_contact(frames,R2/"contact.png")
    save_preview(frames,DURATIONS,R2/"preview.gif")
    save_preview(frames,[500]*8,R2/"preview-slow.gif")
    save_preview(frames,DURATIONS,R2/"preview-native.gif",display_size=(192,208))
    comparisons=[]
    for f in frames:
        pair=Image.new("RGBA",(384,232))
        pair.paste(idle,(0,24));pair.paste(f,(192,24))
        draw=ImageDraw.Draw(pair)
        draw.text((6,5),"APPROVED GU IDLE",fill="white")
        draw.text((198,5),"RIGHT DRAG / CANDIDATE",fill="white")
        draw.line((0,227,383,227),fill=(83,109,95,255))
        comparisons.append(pair)
    save_preview(comparisons,DURATIONS,R2/"idle-comparison.gif",display_size=(768,464))
    # Separate sampling on light and dark backgrounds exposes fringe/tearing.
    detail=Image.new("RGB",(4*320,2*480),(35,38,44))
    d=ImageDraw.Draw(detail)
    for i,f in enumerate(frames):
        x=(i%4)*320;y=(i//4)*480
        if i%2:
            d.rectangle((x,y,x+319,y+479),fill=(212,215,220))
        cut=f.crop((48,76,128,190)).resize((320,456),Image.Resampling.NEAREST)
        detail.paste(cut,(x,y+24),cut.getchannel("A"))
        d.text((x+5,y+5),f"{i+1:02d} / COLLAR ARMS KNEES",fill=(120,120,120))
    detail.save(R2/"seam-detail.png")
    diffs=[]
    for i in range(8):
        f=np.array(frames[i]);n=np.array(frames[(i+1)%8])
        overlay=np.zeros_like(f)
        both=(f[:,:,3]>0)&(n[:,:,3]>0)
        overlay[both]=[200,200,200,255]
        overlay[(f[:,:,3]>0)&~both]=[255,100,180,255]
        overlay[(n[:,:,3]>0)&~both]=[70,220,255,255]
        diffs.append(Image.fromarray(overlay))
    save_contact(diffs,R2/"adjacent-silhouettes.png")
    joins=[int(np.abs(row_offsets((i+1)%8)-row_offsets(i)).max()) for i in range(8)]
    report={"status":"STRUCTURAL_PASS_VISUAL_REVIEW_PENDING",
        "userApproval":"PENDING","runtimeIntegrated":False,
        "frameCount":8,"stripSize":[1536,208],"durationMs":DURATIONS,
        "headPixelLock":"all y<88, same coordinates as canonical Idle",
        "motionMethod":"continuous small integer scanline displacements anchored at neck; no resampling, rotation, limb x-split, blending or source pixel deletion",
        "scope":"suspended right drag only; no replacement of any active asset",
        "dynamicBrowserReview":"NOT_VERIFIED_FILE_URL_BLOCKED_BY_BROWSER_POLICY",
        "sourcePixelCount":int((source[:,:,3]>0).sum()),
        "frames":reports,"adjacentMaxDxIncludingLoop":joins,
        "uniqueFrames":len({f.tobytes() for f in frames}),
        "checksPassed":all(all(f["checks"].values()) for f in reports) and max(joins)<=3,
        "sourceBodyHash":sha(R2/"source-body-edit.png"),"baseHash":sha(R2/"suspended-base.png")}
    (R2/"validation.json").write_text(json.dumps(report,indent=2)+"\n")
    if not report["checksPassed"]:
        raise RuntimeError("Candidate structural checks failed; do not present as ready")
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<title>Gu 向右拖拽 · 后颈悬提摆荡候选</title><style>
body{background:#202329;color:#eee;font:16px system-ui;margin:26px;line-height:1.65}
img{image-rendering:pixelated;max-width:100%;height:auto}a{color:#a4d5ff}
.grid{display:flex;gap:24px;flex-wrap:wrap}figure{margin:0}small{color:#bdc2cd}
</style><h1>Gu Right · 后颈悬提、轻微摆荡</h1>
<p>仅此动作候选，等待人工审核；未接入 App。Feng Look 补帧已延后，其余三项拖拽不变。</p>
<p>8 帧，120 ms/帧（与当前 Drag 播放间隔一致）。头部、眼镜、脸、脖颈锁定原 Idle 像素。
身体/手臂/双腿一起在颈部锚点下方摆荡；双脚离原地面线 10 px，不做踏步。
衣服采用原 Idle 像素，小腿使用局部编辑素材；没有整人缩放。</p>
<h2>Idle 对照 / 原速</h2><img src="idle-comparison.gif" width="768">
<div class="grid"><figure><h2>原尺寸</h2><img src="preview-native.gif" width="192"></figure>
<figure><h2>2× 原速</h2><img src="preview.gif" width="384"></figure>
<figure><h2>2× 慢速审查</h2><img src="preview-slow.gif" width="384"></figure></div>
<h2>全部 8 帧</h2><a href="contact.png"><img src="contact.png"></a>
<h2>衣领 / 手肘 / 袖口 / 膝部细节</h2><a href="seam-detail.png"><img src="seam-detail.png"></a>
<h2>相邻轮廓，最后一格为 8→1</h2><img src="adjacent-silhouettes.png">
<p><a href="validation.json">技术检查</a> · <a href="review-status.json">自检与审批状态</a> ·
<a href="gu-running-right.png">1536×208 RGBA 候选条带</a></p>
<small>GIF 灰底、编号、绿线只用于审核；PNG 素材为真正透明背景。首版比例不合格的身体图已否决，未进入本动画。</small>
</html>'''
    (R2/"index.html").write_text(page)
    print(json.dumps(report,indent=2))


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
    parser.add_argument("command", choices=["normalize", "normalize-r2", "animate"])
    args = parser.parse_args()
    {"normalize":normalize, "normalize-r2":normalize_r2,"animate":animate}[args.command]()
