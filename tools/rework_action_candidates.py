#!/usr/bin/env python3
"""Review-only original-pixel repairs; never writes approved/runtime selections."""
from pathlib import Path
import sys
import json
import hashlib
import math
from collections import deque

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.repair_reviewed_actions import frame, difference, pair_sheet
from tools.build_animation_review import save_contact, save_preview

SOURCE = ROOT/"assets/rework/v0.1.0/action-repair-2026-10-02"
OUT = ROOT/"assets/rework/v0.1.0/action-rework-r2-2026-10-03"


def diagnostics():
    folder = OUT/"diagnosis"
    folder.mkdir(parents=True,exist_ok=True)
    atlas=Image.open(SOURCE/"feng.webp").convert("RGBA")
    for row,count,name in [(0,6,"idle"),(3,4,"waving"),(5,8,"failed"),(8,6,"review"),(9,8,"look")]:
        frames=[frame(atlas,row,i) for i in range(count)]
        save_contact(frames,folder/f"feng-{name}.png")
        if row in (0,3,8,9):
            crop=frames[0].crop((35,25,160,155)).resize((500,520),Image.Resampling.NEAREST)
            canvas=Image.new("RGBA",crop.size,(70,30,65,255));canvas.alpha_composite(crop)
            canvas.convert("RGB").save(folder/f"feng-{name}-detail.png")


def exterior(alpha):
    """Only transparency reachable from canvas border, not holes in clothing."""
    h,w=alpha.shape
    seen=np.zeros((h,w),bool)
    queue=deque([(x,0) for x in range(w)]+[(x,h-1) for x in range(w)]+
                [(0,y) for y in range(h)]+[(w-1,y) for y in range(h)])
    while queue:
        x,y=queue.popleft()
        if x<0 or y<0 or x>=w or y>=h or alpha[y,x] or seen[y,x]: continue
        seen[y,x]=True
        queue.extend(((x-1,y),(x+1,y),(x,y-1),(x,y+1)))
    return seen


def clean_edge(original):
    p=np.array(original)
    original_array=p.copy()
    for _ in range(2):
        outside=exterior(p[:,:,3]>0)
        adjacent=np.asarray(Image.fromarray(outside.astype(np.uint8)*255).filter(ImageFilter.MaxFilter(3)))>0
        rgb=p[:,:,:3].astype(int)
        # Exterior neutral matte only. Internal shirt, collar, belt and eye
        # highlights cannot be reached through small enclosed alpha holes.
        neutral=(rgb.max(2)-rgb.min(2)<=40)&(rgb.min(2)>=85)
        cut=adjacent & (p[:,:,3]>0) & neutral
        # Approved shirt core and buckle are explicitly protected.
        cut[64:119,80:110]=False
        cut[112:124,83:108]=False
        p[cut]=0
    changed=np.any(p!=original_array,axis=2)
    return Image.fromarray(p), int(changed.sum())


def write_candidate(name,frames,lengths,originals=None):
    folder=OUT/name; folder.mkdir(parents=True,exist_ok=True)
    strip=Image.new("RGBA",(192*len(frames),208))
    for i,im in enumerate(frames):
        im.save(folder/f"{i+1:02d}.png");strip.paste(im,(192*i,0))
    strip.save(folder/f"{Path(name).name}.png")
    save_preview(frames,lengths,folder/"preview.gif")
    save_contact(frames,folder/"contact.png")
    selected=frames[1] if name=="feng-failed-keyposes" else frames[0]
    closeup=selected.crop((35,25,160,155)).resize((500,520),Image.Resampling.NEAREST)
    board=Image.new("RGBA",closeup.size,(70,30,65,255));board.alpha_composite(closeup)
    board.save(folder/"detail.png")
    if originals:
        pair_sheet(originals,frames,folder/"comparison.png")
        for i,(a,b) in enumerate(zip(originals,frames)):
            difference(a,b)[0].save(folder/f"diff-{i+1:02d}.png")


def edges():
    original=Image.open(ROOT/"assets/builds/feng/spritesheet.webp").convert("RGBA")
    selected=Image.open(SOURCE/"feng.webp").convert("RGBA")
    report=[]
    for name,count,row in [("feng-waving-edge",4,3),("feng-review-edge",6,8),("feng-look-edge",16,9)]:
        src=selected if count==16 else original
        originals=[frame(src,row+i//8,i%8) for i in range(count)]
        results=[clean_edge(im) for im in originals]
        new=[im for im,_ in results]
        write_candidate(name,new,[180]*count,originals)
        report.append({"candidate":name,"removedPixels":[n for _,n in results],
                       "restoredOriginalClothing":count!=16,"status":"REQUIRES_VISUAL_REVIEW"})
    return report


def failed_keyposes():
    atlas=Image.open(SOURCE/"feng.webp").convert("RGBA")
    idle=frame(atlas,0,0)
    # The approved Review chest-hand pose supplies existing forearm/jacket and
    # the face pixels formerly occluded by the finger. No synthetic limb warp.
    donor=frame(atlas,8,2)
    mask=Image.new("L",(192,208))
    painter=ImageDraw.Draw(mask)
    # Keep a complete existing head/neck silhouette. Never splice one frame's
    # jaw onto another frame's eyes: the 1 px pose change produces a cheek notch.
    painter.rectangle((0,0,191,70),fill=255)
    painter.polygon([(39,61),(65,57),(65,48),(111,48),(114,70),(110,115),(39,115)],fill=255)
    chest=idle.copy();chest.paste(donor,(0,0),mask)
    # No cleanup of the head; only donor sleeve's exterior may be corrected.
    cleaned,_=clean_edge(chest)
    sleeve=mask.copy();ImageDraw.Draw(sleeve).rectangle((0,0,191,70),fill=0)
    chest.paste(cleaned,(0,0),sleeve)
    closed=chest.copy()
    blink=frame(atlas,0,3)
    # Approved idle blink pixels only; retain face boundary, glasses and hair.
    closed.paste(blink.crop((72,35,111,47)),(72,35))
    frames=[idle,chest,closed,idle.copy()]
    write_candidate("feng-failed-keyposes",frames,[450,400,450,500],[idle]*4)
    return {"candidate":"feng-failed-keyposes","runtimeFramesRepresented":[1,4,5,8],
            "notCompleteAnimation":True,"armDonor":"feng review frame 03",
            "blinkDonor":"feng idle frame 04","headDonor":"complete approved review frame 03 head, no mixed face silhouette",
            "status":"REQUIRES_VISUAL_REVIEW"}


def pose_leg(source, hip, split, side, dx, lift):
    """Local integer row reposition only. Palette unchanged; no body scaling.

    Root stays attached. Shoe rows move together. Swing knee advances before
    the shoe; swing shoe clearance is limited to 2 px. This is a candidate,
    not an anatomical/visual approval.
    """
    src=np.asarray(source); dst=np.zeros_like(src)
    for y in range(hip,208):
        p=min(1,max(0,(y-hip)/(190-hip)))
        bend=round((1-p)*p*4*(1 if lift else 0))
        shift=round(dx*p)+bend
        yy=y-round(lift*p)
        xs=range(0,split) if side==0 else range(split,192)
        for x in xs:
            if src[y,x,3] and 0<=x+shift<192:
                dst[yy,x+shift]=src[y,x]
    return Image.fromarray(dst)


def drag_candidates():
    reports=[]
    for form in ("gu","feng"):
        atlas=Image.open(SOURCE/f"{form}.webp").convert("RGBA")
        # Original low, planted stance, not the rejected shuffle reference.
        source=frame(atlas,1,6)
        hip,split=(143,100) if form=="gu" else (128,100)
        # Each limb alternates planted-backward and lifted-forward phases.
        # Opposite half-cycle gives genuine alternation rather than eight
        # successive variants of the same lifted leg.
        path=[(6,0),(3,0),(0,0),(-3,0),(-6,0),(-3,2),(0,2),(3,1)]
        result=[];metrics=[]
        for i in range(8):
            top=frame(atlas,1,i)
            # Keep existing upper-body/arm motion, but a fixed two-row hip
            # root avoids copying eight incompatible pelvis silhouettes.
            top.paste(source.crop((0,hip-5,192,hip)),(0,hip-5))
            top.paste(Image.new("RGBA",(192,208-hip)),(0,hip))
            for side,index in [(1,(i+4)%8),(0,i)]:
                dx,lift=path[index]
                top.alpha_composite(pose_leg(source,hip,split,side,dx,lift))
            result.append(top)
            metrics.append({"frame":i+1,"left":path[i],"right":path[(i+4)%8],
                            "bbox":top.getchannel("A").getbbox()})
        old=[frame(atlas,1,i) for i in range(8)]
        write_candidate(f"diagnosis/rejected-drag/{form}-drag-right",result,[140]*8,old)
        # Existing direction-left source is the approved deterministic mirror;
        # use the same same-order per-cell operation, never flip the strip.
        left=[im.transpose(Image.Transpose.FLIP_LEFT_RIGHT) for im in result]
        write_candidate(f"diagnosis/rejected-drag/{form}-drag-left",left,[140]*8,[frame(atlas,2,i) for i in range(8)])
        reports.append({"form":form,"source":"original running-right frame 07", "hip":hip,
                        "split":split,"stepTrajectory":metrics,"status":"SELF_CHECK_FAIL_DO_NOT_USE",
                        "reason":"fixed-x leg split cuts overlapping limb pixels; visible vertical trouser tear",
                        "nextGate":"MANUAL_LEG_KEYPOSE_REVIEW_REQUIRED",
                        "originalUpperMotionRetainedAbove":hip-5})
    return reports


def review_page(report):
    rows=[]
    reviewed_path=OUT/"review-status.json"
    reviewed=json.loads(reviewed_path.read_text()) if reviewed_path.exists() else None
    descriptions={
        "feng-waving-edge":"Feng Waving · 白边/衣领及腰带恢复",
        "feng-review-edge":"Feng Review · 仅外轮廓去白边",
        "feng-look-edge":"Feng Look · 保留已通过肩部动作，修外围白边",
        "feng-failed-keyposes":"Feng Failed · 01/04/05/08 关键姿势，不是完整八帧动画",
    }
    selected=Image.open(SOURCE/"feng.webp").convert("RGBA")
    for name,row,count in [("feng-waving-edge",3,4),("feng-review-edge",8,6),("feng-look-edge",9,16),
                            ("feng-failed-keyposes",5,8)]:
        before=[frame(selected,row+i//8,i%8) for i in range(count)]
        if not reviewed:
            save_preview(before,[180]*count,OUT/name/"previous.gif")
        verdict=reviewed["items"][name] if reviewed else None
        label=("用户通过 · 已锁定" if verdict["status"]=="USER_APPROVED" else "用户否决 · 撤回 / 禁止使用") if verdict else "待审核"
        rows.append(f'<tr><th>{descriptions[name]}<p>{label}</p></th><td><img src="{name}/previous.gif"></td>'
                    f'<td><img src="{name}/preview.gif"><p><a href="{name}/preview.gif">GIF</a> · '
                    f'<a href="{name}/contact.png">逐帧图</a> · '
                    f'<a href="{name}/comparison.png">源像素对照 / 差异</a> · '
                    f'<a href="{name}/detail.png">高对比背景放大</a></p></td></tr>')
    page='''<!doctype html><meta charset="utf-8"><title>返工第二轮 · 待审核</title>
<style>body{background:#20232a;color:#eee;font:16px system-ui;padding:22px}a{color:#91c9ff}
table{border-collapse:collapse}td,th{border:1px solid #60656d;padding:15px}img{width:384px;image-rendering:pixelated}
th{max-width:260px;text-align:left}p{line-height:1.6}</style>
<h1>返工第二轮 · 人工审核前不接入 App</h1>
<p>白边只处理 Feng Waving / Review / Look。Gu 已通过素材不改。GIF 背景用于观察残边，PNG 源仍透明。
Failed 本轮只有四张关键姿势；姿势通过后才补齐八帧，不能把此 GIF 当作最终动作连续性验收。</p>
<p><strong>左右拖拽：自检 FAIL，停止当前局部变形方案。</strong>固定左右切分切坏了交叉裤腿。
未接入、未覆盖原片；不以新失败结果作为下轮基础。
<a href="diagnosis/rejected-drag/gu-drag-right/contact.png">Gu 失败证据</a> ·
<a href="diagnosis/rejected-drag/feng-drag-right/contact.png">Feng 失败证据</a>。
后续需人工确认“前脚接地 / 后脚蹬离 / 摆动经过 / 换脚接地”四个腿部姿势，不能继续横切挪动原腿。</p>
<table><tr><th>动作</th><th>上轮素材</th><th>本轮候选</th></tr>'''
    if reviewed:
        page=page.replace("返工第二轮 · 待审核","返工第二轮 · 审核结论")
        page=page.replace("<h1>返工第二轮 · 人工审核前不接入 App</h1>","<h1>已审核：Waving / Review 通过；Look / Failed 失败</h1><p><strong>Look 与 Failed 以下图片仅作失败证据，不再是待审候选。没有部署。此前 11 项技术检查不构成视觉通过。</strong></p>")
    (OUT/"index.html").write_text(page+''.join(rows)+'</table>')


if __name__=="__main__":
    if (OUT/"review-status.json").exists():
        raise SystemExit("R2 has been reviewed and locked. Do not overwrite approved art or regenerate rejected candidates.")
    frozen=[SOURCE/"gu.webp",SOURCE/"feng.webp",ROOT/"assets/builds/gu/spritesheet.webp",
            ROOT/"assets/builds/feng/spritesheet.webp",ROOT/"standalone-app/asset-overrides.json"]
    before={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in frozen}
    diagnostics()
    report={"edges":edges(),"failed":failed_keyposes(),"drag":drag_candidates()}
    report["inputs"]=before
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==sha for p,sha in before.items())
    report["sourceAndSelectionUnchanged"]=True
    report["candidateOnly"]=True
    review_page(report)
    (OUT/"report.json").write_text(json.dumps(report,indent=2)+"\n")
