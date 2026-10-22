"""Derive a leftward sway from approved right pixels, without mirroring identity."""
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.prepare_gu_drag_suspended import OUT as RIGHT_ROOT, sha
from tools.build_gu_drag_suspended import R2 as RIGHT, row_offsets, DURATIONS
from tools.build_animation_review import save_preview, save_contact
from tools.finish_feng_look_r6 import components

OUT = ROOT / "assets/rework/v0.1.0/gu-drag-left-suspended-2026-10-22"


def verify_right_source(folder=RIGHT):
    record = json.loads((folder / "review-status.json").read_text())
    if (record.get("status") != "GU_DRAG_RIGHT_ART_APPROVED"
            or record.get("userApproval") != "APPROVED"
            or not record.get("generatorLocked")):
        raise ValueError("Right source is not approved and frozen")
    required = {f"right-{i:02d}.png" for i in range(1,9)} | {"gu-running-right.png"}
    if not required <= record.get("sha256", {}).keys():
        raise ValueError("Right source freeze is incomplete")
    for name, digest in record["sha256"].items():
        if Path(name).name != name:
            raise ValueError("Invalid source filename")
        if sha(folder / name) != digest:
            raise ValueError(f"Frozen right source changed: {name}")
    return record


def assert_unapproved(folder=OUT):
    status = folder / "review-status.json"
    if status.exists() and json.loads(status.read_text()).get("generatorLocked"):
        raise RuntimeError("Approved Gu left drag is frozen; create a new revision")


def derive_left(right, index):
    if not 0 <= index < 8:
        raise ValueError("Frame index must be 0..7")
    if right.mode != "RGBA" or right.size != (192,208):
        raise ValueError("Expected 192x208 RGBA source")
    source = np.array(right)
    if set(np.unique(source[:,:,3])) - {0,255} or source[source[:,:,3]==0,:3].any():
        raise ValueError("Source must have binary alpha and zero hidden RGB")
    target = np.zeros_like(source)
    for y, delta in enumerate(-2 * row_offsets(index)):
        xs = np.flatnonzero(source[y,:,3])
        if len(xs) and (xs[0]+delta < 0 or xs[-1]+delta >=192):
            raise ValueError("Left displacement would clip source pixels")
        # Bijective translation: not a horizontal flip, warp/resample or x-split.
        target[y,xs+delta] = source[y,xs]
    return Image.fromarray(target)


def checks(left, right, idle, index):
    p=np.array(left);r=np.array(right);canonical=np.array(idle)
    bbox=left.getbbox()
    left_offsets=-row_offsets(index)
    next_offsets=-row_offsets((index+1)%8)
    results={
        "rgba192x208":left.mode=="RGBA" and left.size==(192,208),
        "headNeckIdleExact":bool(np.array_equal(p[:88],canonical[:88])),
        "binaryAlpha":set(np.unique(p[:,:,3]))=={0,255},
        "zeroHiddenRgb":not bool(p[p[:,:,3]==0,:3].any()),
        "noNewColors":{tuple(c) for c in p[p[:,:,3]>0]}=={tuple(c) for c in r[r[:,:,3]>0]},
        "sameOccupiedPixelsPerRow":bool(np.array_equal((p[:,:,3]>0).sum(1),(r[:,:,3]>0).sum(1))),
        "oneConnectedFigure":len(components(left))==1,
        "safeMargins":bbox[0]>=4 and bbox[1]>=4 and bbox[2]<=188 and bbox[3]<=204,
        "feetAirborneAt193":bbox[3]-1==193,
        "positiveBodyLag":all(left_offsets[y]>0 for y in [130,150,193]),
        "maxAdjacentStep3IncludingLoop":int(np.abs(next_offsets-left_offsets).max())<=3,
        "maxRowStep1":int(np.abs(np.diff(left_offsets)).max())<=1,
    }
    return {"frame":index+1,"bbox":list(bbox),"footY":bbox[3]-1,
            "neckDx":int(left_offsets[88]),"waistDx":int(left_offsets[130]),
            "handsDx":int(left_offsets[150]),"shoesDx":int(left_offsets[193]),
            "nextMaxDx":int(np.abs(next_offsets-left_offsets).max()),"checks":results}


def comparison(sets, labels):
    result=[]
    for i in range(8):
        canvas=Image.new("RGBA",(192*len(sets),232))
        d=ImageDraw.Draw(canvas)
        for j,frames in enumerate(sets):
            canvas.paste(frames[i],(192*j,24))
            d.text((192*j+6,5),labels[j],fill="white")
        d.line((0,227,canvas.width-1,227),fill=(83,109,95,255))
        result.append(canvas)
    return result


def build(output=OUT):
    assert_unapproved(output)
    approval=verify_right_source()
    idle_path=RIGHT_ROOT/"canonical-idle.png"
    idle=Image.open(idle_path).convert("RGBA")
    rights=[Image.open(RIGHT/f"right-{i:02d}.png").convert("RGBA") for i in range(1,9)]
    lefts=[derive_left(f,i) for i,f in enumerate(rights)]
    reports=[checks(f,rights[i],idle,i) for i,f in enumerate(lefts)]
    if len({f.tobytes() for f in lefts})!=8 or not all(all(r["checks"].values()) for r in reports):
        raise RuntimeError("Left structural QA failed before artifact writes")
    sources=[RIGHT/name for name in approval["sha256"]]
    sources += [RIGHT/"review-status.json",RIGHT/"validation.json",idle_path,
        ROOT/"tools/build_gu_drag_suspended.py", ROOT/"assets/builds/gu/spritesheet.webp",
        ROOT/"assets/builds/feng/spritesheet.webp",ROOT/"standalone-app/asset-overrides.json"]
    before={str(p.relative_to(ROOT)):sha(p) for p in sources}
    output.mkdir(parents=True,exist_ok=True)
    strip=Image.new("RGBA",(1536,208))
    for i,f in enumerate(lefts):
        f.save(output/f"left-{i+1:02d}.png")
        strip.paste(f,(192*i,0))
    strip.save(output/"gu-running-left.png")
    save_contact(lefts,output/"contact.png")
    save_preview(lefts,DURATIONS,output/"preview.gif")
    save_preview(lefts,[500]*8,output/"preview-slow.gif")
    save_preview(lefts,DURATIONS,output/"preview-native.gif",display_size=(192,208))
    save_preview(comparison([[idle]*8,lefts],["APPROVED GU IDLE","LEFT DRAG / CANDIDATE"]),
        DURATIONS,output/"idle-comparison.gif",display_size=(768,464))
    save_preview(comparison([rights,[idle]*8,lefts],["RIGHT / APPROVED","GU IDLE","LEFT / CANDIDATE"]),
        DURATIONS,output/"right-left-comparison.gif",display_size=(1152,464))
    detail=Image.new("RGB",(1152,800),(35,38,44));d=ImageDraw.Draw(detail)
    for i,f in enumerate(lefts):
        x=i%4*288;y=i//4*400
        if i%2:
            d.rectangle((x,y,x+287,y+399),fill=(212,215,220))
        crop=f.crop((48,76,144,200)).resize((288,372),Image.Resampling.NEAREST)
        detail.paste(crop,(x,y+24),crop.getchannel("A"))
        d.text((x+6,y+6),f"{i+1:02d} / COLLAR CUFF KNEE SHOE",fill=(120,120,120))
    detail.save(output/"seam-detail.png")
    differences=[]
    for i,frame in enumerate(lefts):
        a=np.array(frame)[:,:,3]>0;b=np.array(lefts[(i+1)%8])[:,:,3]>0
        overlay=np.zeros((208,192,4),dtype=np.uint8)
        overlay[a&b]=[200,200,200,255]
        overlay[a&~b]=[255,100,180,255]
        overlay[b&~a]=[70,220,255,255]
        differences.append(Image.fromarray(overlay))
    save_contact(differences,output/"adjacent-silhouettes.png")
    after={str(p.relative_to(ROOT)):sha(p) for p in sources}
    if after!=before:
        raise RuntimeError("Protected source changed during candidate build")
    manifest={"status":"GENERATED_FOR_REVIEW","scope":"gu-running-left-only",
        "sourceApproval":"GU_DRAG_RIGHT_ART_APPROVED", "sourceApprovalCommit":"5d84dde",
        "sourceHashes":before,"method":"same-order approved right PNGs, per-row delta=-2*right_offset; identity not mirrored",
        "imagegenUsed":False,"resamplingUsed":False,"runtimeIntegrated":False}
    (output/"source-manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    report={"status":"STRUCTURAL_PASS_VISUAL_REVIEW_PENDING","userApproval":"PENDING",
        "runtimeIntegrated":False,"stripSize":[1536,208],"frameCount":8,"durationsMs":DURATIONS,
        "uniqueFrames":len({f.tobytes() for f in lefts}),"sourceFilesUnchanged":True,
        "checksPassed":True,"frames":reports,
        "dynamicPlayback":"NOT_VERIFIED_BY_AGENT; GIF supplied for user review",
        "appRuntime":"NOT_TESTED; no asset override or live App change"}
    (output/"validation.json").write_text(json.dumps(report,indent=2)+"\n")
    (output/"index.html").write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<title>Gu 左拖拽 · 后颈悬提摆荡候选</title><style>
body{background:#202329;color:#eee;font:16px system-ui;margin:26px;line-height:1.65}
img{image-rendering:pixelated;max-width:100%;height:auto}a{color:#a4d5ff}
.grid{display:flex;gap:24px;flex-wrap:wrap}figure{margin:0}small{color:#bdc2cd}</style>
<h1>Gu Left · 向左悬提、身体向右滞后</h1>
<p>8 帧候选，120 ms/帧。头部与脖颈保留 Idle 原像素、原位置；不镜像发型和脸。
仅反转已批准右向运动的身体位移；不重新生成、不缩放。未接入 App，待用户审核。</p>
<h2>Idle 对照 / 原速</h2><img src="idle-comparison.gif" width="768">
<h2>右向已批准 / Idle / 左向候选</h2><img src="right-left-comparison.gif" width="1152">
<div class="grid"><figure><h2>原尺寸</h2><img src="preview-native.gif" width="192"></figure>
<figure><h2>2× 原速</h2><img src="preview.gif" width="384"></figure>
<figure><h2>慢速逐帧</h2><img src="preview-slow.gif" width="384"></figure></div>
<h2>全部 8 帧</h2><a href="contact.png"><img src="contact.png"></a>
<h2>明暗底细节</h2><a href="seam-detail.png"><img src="seam-detail.png"></a>
<h2>相邻轮廓（最后一格 8→1）</h2><img src="adjacent-silhouettes.png">
<p><a href="validation.json">技术检查</a> · <a href="review-status.json">自检及审批状态</a> ·
<a href="source-manifest.json">来源与冻结哈希</a> · <a href="gu-running-left.png">透明 PNG 条带</a></p>
<small>GIF 中背景、编号、地面参考线仅用于审阅，生产 PNG 无背景。Feng Look 补帧仍延后。</small></html>
''')
    return report


if __name__ == "__main__":
    print(json.dumps(build(),indent=2))
