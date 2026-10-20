"""Extract generated cardinal heads for review with a frozen canonical body."""
from pathlib import Path
import sys
import json
import hashlib
from collections import deque

import numpy as np
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.build_animation_review import save_preview,save_contact
from tools.prepare_feng_look_r6 import OUT,assert_unapproved,gu_references


def masks(idle):
    """Canonical Idle anatomical masks; no rejected R5 image dependency."""
    head=np.zeros((208,192),bool);head[:48]=True
    spans=[(74,108),(75,106),(76,105),(77,104),(78,103),(79,102),
           (80,101),(81,100),(82,99),(84,98),(86,97),(88,95),(89,93)]
    for y,(l,r) in enumerate(spans,48):head[y,l:r]=True
    head &= np.array(idle)[:,:,3]>0
    foreground=np.zeros((208,192),bool)
    fingers={49:(85,88),50:(84,89),51:(83,90),52:(83,90),53:(83,90),
             54:(83,90),55:(83,90),56:(82,90),57:(82,90),58:(82,90),
             59:(81,91),60:(80,93)}
    for y,(l,r) in fingers.items():foreground[y,l:r]=True
    foreground[61:]=True
    return head,foreground


def extract():
    assert_unapproved()
    raw=Image.open(OUT/"source-imagegen.png").convert("RGBA")
    result=[]
    scale=200/535
    for i in range(4):
        half=raw.width//2
        x=(i%2)*half;y=(i//2)*half
        cell=raw.crop((x,y,x+half,y+half))
        a=np.array(cell)
        a[a[:,:,3]<128]=0
        a[a[:,:,3]>=128,3]=255
        box=Image.fromarray(a).getchannel("A").getbbox()
        subject=Image.fromarray(a).crop(box)
        size=(round(subject.width*scale),round(subject.height*scale))
        subject=subject.resize(size,Image.Resampling.NEAREST)
        canvas=Image.new("RGBA",(192,208))
        position=(96-subject.width//2,204-subject.height)
        canvas.paste(subject,position)
        canvas.save(OUT/f"raw-normalized-{i+1:02d}.png")
        result.append(canvas)
    save_contact(result,OUT/"raw-normalized-contact.png",columns=4)
    detail=Image.new("RGB",(384*4,480),(62,29,61))
    d=ImageDraw.Draw(detail)
    for i,im in enumerate(result):
        crop=im.crop((48,0,144,110)).resize((384,440),Image.Resampling.NEAREST)
        detail.paste(crop,(i*384,30),crop.getchannel("A"))
        d.text((i*384+8,8),str(i),fill="white")
    detail.save(OUT/"raw-normalized-detail.png")
    for i,im in enumerate(result):
        box=(65,40,118,78)
        crop=im.crop(box).resize((636,456),Image.Resampling.NEAREST)
        board=Image.new("RGB",(676,486),(62,29,61));board.paste(crop,(40,30),crop.getchannel("A"))
        draw=ImageDraw.Draw(board)
        for x in range(66,118,2):draw.text((40+(x-65)*12,5),str(x),fill="white")
        for y in range(40,78):draw.text((3,30+(y-40)*12),str(y),fill="white")
        board.save(OUT/f"face-grid-{i+1:02d}.png")
    return result


def composite_trial(raw_frames):
    """Candidate-only composition. Body and foreground are exact Idle bytes."""
    assert_unapproved()
    idle=Image.open(OUT/"canonical-idle.png").convert("RGBA")
    source=np.array(idle)
    old_head,foreground=masks(idle)
    head_masks=[]
    # Anatomically traced chin/neck contours, excluding generated clothing.
    spans=[
        [(74,111),(75,108),(76,106),(77,104),(79,103),(81,103),
         (83,102),(85,102),(87,101),(89,101),(90,101),(91,101),(92,101)],
        [(74,111),(76,109),(77,108),(79,107),(81,106),(83,105),
         (85,104),(87,104),(89,103),(90,102),(90,102),(91,101),(92,101)],
        [(75,108),(76,107),(77,106),(78,105),(79,104),(80,103),
         (81,102),(82,101),(83,100),(84,99),(85,99),(86,98),(88,97)],
        [(72,107),(73,105),(74,103),(75,101),(76,100),(78,100),
         (80,100),(82,100),(84,100),(86,100),(88,100),(90,100),(91,100)],
    ]
    # Source fingers are separate from head art: erase their visible upper
    # segments with adjacent face planes before restoring the frozen hand.
    fingers=[
        [(y,83,88,91) for y in range(42,50)],
        [(48,91,95,97),(49,91,96,98),(50,91,96,98),(51,90,96,98),
         (52,89,96,98),(53,88,95,98),(54,87,94,96),(55,86,93,95),
         (56,85,93,95),(57,85,92,94),(58,84,92,94),(59,84,91,94),(60,84,91,94)],
        [(y,86,92,94) for y in range(54,61)],
        [(y,82,89,91) for y in range(50,61)],
    ]
    output=[]
    for i,raw in enumerate(raw_frames):
        p=np.array(raw)
        for y,l,r,sample in fingers[i]:p[y,l:r]=p[y,sample]
        head=np.zeros((208,192),bool);head[:48]=True
        for y,(l,r) in enumerate(spans[i],48):head[y,l:r]=True
        head &= p[:,:,3]>0
        p[~head]=0
        # A common 0.925 nearest-neighbour art normalization, not a head-turn
        # warp. Turn perspective comes exclusively from the generated art.
        layer=Image.fromarray(p).crop((55,0,130,61))
        layer=layer.resize((69,56),Image.Resampling.NEAREST)
        turned=Image.new("RGBA",(192,208));turned.paste(layer,(58,0))
        t=np.array(turned)
        body=source.copy();body[old_head & ~foreground]=0
        # Reconstruct only the short neck under the new jaw, behind the exact
        # original hand. No sleeve/lapel/shoulder pixel is editable.
        for y in range(49,61):
            for x in range(87,104):
                if old_head[y,x] and not foreground[y,x]:
                    body[y,x]=source[59,min(103,max(93,x))]
        mutable=(old_head | (source[:,:,3]==0)) & ~foreground
        mutable[61:]=False
        visible=(t[:,:,3]>0)&mutable
        body[visible]=t[visible]
        body[foreground]=source[foreground]
        body[body[:,:,3]==0]=0
        im=Image.fromarray(body);im.save(OUT/f"trial-cardinal-{i+1:02d}.png")
        output.append(im)
    save_contact([idle]+output,OUT/"trial-idle-contact.png",columns=5)
    board=Image.new("RGB",(400*5,480),(55,29,55))
    for i,im in enumerate([idle]+output):
        crop=im.crop((50,0,130,94)).resize((400,470),Image.Resampling.NEAREST)
        board.paste(crop,(400*i,10),crop.getchannel("A"))
    board.save(OUT/"trial-heads.png")
    return output


def clean_head_candidates():
    assert_unapproved()
    raw=Image.open(OUT/"source-heads-only.png").convert("RGBA")
    idle=Image.open(OUT/"canonical-idle.png").convert("RGBA")
    source=np.array(idle)
    palette=np.unique(source[:48][source[:48,:,3]>0,:3],axis=0).astype(np.int32)
    _,foreground=masks(idle)
    removable=np.zeros((208,192),bool);removable[:48]=True
    for y,(l,r) in enumerate([(73,110),(73,109),(74,108),(74,107),(75,107),
                              (76,106),(77,106),(78,106),(79,106),(80,105),
                              (81,105),(82,104),(83,103)],48):
        removable[y,l:r]=True
    # Protect every existing blue suit and pale collar pixel below the ear.
    rgb=source[:,:,:3].astype(int)
    clothing=(rgb[:,:,2]>rgb[:,:,0]+8)|((rgb.min(2)>145)&(rgb.max(2)-rgb.min(2)<45))
    clothing[:48]=False
    protected=foreground|clothing
    removable &= ~protected
    body=source.copy();body[removable]=0
    # Continuous neck behind the exact, stationary hand and collar. Its lower
    # portion uses the existing Idle neck, not a generated sleeve/shoulder.
    neck=Image.new("L",(192,208))
    ImageDraw.Draw(neck).polygon([(86,44),(103,44),(103,55),(96,65),(86,61)],fill=255)
    nm=(np.array(neck)>0)&removable
    for y,x in zip(*np.where(nm)):
        body[y,x]=source[56 if x>98 else 58,99 if x>98 else 96]
    body[protected]=source[protected]
    frames=[]
    half=raw.width//2
    # One shared head-only raster normalization to the canonical 49x57 head
    # reference. X/Y factors are recorded separately: this is not a uniform
    # scale, and must not be reported as untouched head proportions. No frame
    # receives its own bbox fit. The body is not resampled at all.
    scale_x=49/356
    scale_y=57/366
    for i in range(4):
        a=np.array(raw.crop((i%2*half,i//2*half,(i%2+1)*half,(i//2+1)*half)))
        a[a[:,:,3]<128]=0;a[a[:,:,3]>=128,3]=255
        im=Image.fromarray(a);box=im.getbbox()
        head=im.crop(box)
        head=head.resize((round(head.width*scale_x),round(head.height*scale_y)),Image.Resampling.NEAREST)
        layer=Image.new("RGBA",(192,208))
        layer.paste(head,(89-head.width//2,4))
        t=np.array(layer)
        # Reuse existing Idle head colors, nearest palette entry without
        # blending/dither. Generated clothing is never part of this palette.
        for color in np.unique(t[t[:,:,3]>0,:3],axis=0):
            match=palette[np.square(palette-color.astype(np.int32)).sum(1).argmin()]
            t[np.all(t[:,:,:3]==color,axis=2)&(t[:,:,3]>0),:3]=match
        candidate=body.copy()
        allowed=(removable|(source[:,:,3]==0))&~protected
        allowed[61:]=False
        draw=(t[:,:,3]>0)&allowed
        candidate[draw]=t[draw]
        candidate[protected]=source[protected]
        candidate[candidate[:,:,3]==0]=0
        final=Image.fromarray(candidate)
        final.save(OUT/f"cardinal-{i+1:02d}.png");frames.append(final)
    board=Image.new("RGB",(192*5,238),(36,39,45));d=ImageDraw.Draw(board)
    for i,(im,label) in enumerate(zip([idle]+frames,["FENG IDLE / UNCHANGED","000 UP","090 RIGHT","180 DOWN","270 LEFT"])):
        board.paste(im,(192*i,26),im.getchannel("A"));d.text((192*i+5,6),label,fill="white")
    board.save(OUT/"idle-comparison.png")
    board=Image.new("RGB",(400*5,480),(55,29,55))
    for i,im in enumerate([idle]+frames):
        crop=im.crop((50,0,130,94)).resize((400,470),Image.Resampling.NEAREST)
        board.paste(crop,(400*i,10),crop.getchannel("A"))
    board.save(OUT/"head-detail.png")
    Image.fromarray(protected.astype(np.uint8)*255).save(OUT/"protected-mask.png")
    Image.fromarray(removable.astype(np.uint8)*255).save(OUT/"editable-mask.png")
    return frames


def components(im):
    remaining=set(map(tuple,np.argwhere(np.array(im)[:,:,3]>0)))
    sizes=[]
    while remaining:
        queue=deque([remaining.pop()]);count=1
        while queue:
            y,x=queue.popleft()
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    p=(y+dy,x+dx)
                    if p in remaining:remaining.remove(p);queue.append(p);count+=1
        sizes.append(count)
    return sorted(sizes,reverse=True)


def review(frames):
    assert_unapproved()
    idle=Image.open(OUT/"canonical-idle.png").convert("RGBA")
    p=np.array(idle)
    protected=np.array(Image.open(OUT/"protected-mask.png"))>0
    references=gu_references()
    # A four-keypose review, deliberately not claimed to be a finished smooth
    # sixteen-direction animation. No interpolated or fabricated inbetweens.
    save_preview(frames,[700]*4,OUT/"cardinals-preview.gif")
    save_preview([im.crop((54,0,122,88)) for im in frames],[700]*4,
                 OUT/"head-and-hand.gif",display_size=(340,440))
    comparisons=[]
    for direction,ref,candidate in zip(["UP","RIGHT","DOWN","LEFT"],references,frames):
        panel=Image.new("RGBA",(576,232))
        d=ImageDraw.Draw(panel)
        for col,(im,label) in enumerate([(idle,"FENG IDLE / LOCKED"),(ref,"GU / MOTION ONLY"),(candidate,f"FENG / {direction}")]):
            panel.paste(im,(192*col,24));d.text((192*col+5,5),label,fill="white")
        comparisons.append(panel)
    save_preview(comparisons,[850]*4,OUT/"gu-reference-preview.gif",display_size=(1152,464))
    save_contact(frames,OUT/"contact.png",columns=4)
    report={
        "status":"FOUR_CARDINAL_KEYPOSE_CANDIDATE", "userApproval":"PENDING",
        "runtimeIntegrated":False,"complete16DirectionAnimation":False,
        "imagegenUsed":True,"mode":"built-in imagegen; no CLI",
        "sourceIdle":"assets/builds/feng/spritesheet.webp:row0/frame0",
        "officialAtlasSha256":hashlib.sha256((ROOT/"assets/builds/feng/spritesheet.webp").read_bytes()).hexdigest(),
        "headOnlyNormalization":{"xScale":49/356,"yScale":57/366,"resampler":"NEAREST",
                                 "uniformScale":False,"sameFactorsForAllPoses":True},
        "palette":"nearest existing Idle head RGB, no dither or blended color",
        "registrationX":96,"baselineY":203,"sourceHeadReferenceBbox":[64,4,113,61],
        "frames":[],
        "selfReview":{"scope":"native-size and 5x static head/hand/collar comparison",
                      "findings":"Full sleeve, elbow, cuff and suit copied from Idle. First composition rejected for duplicate finger and neck fragments. Head-only edit used for current candidate.",
                      "notClaimed":["user art approval","16-direction continuity","App playback QA"]},
    }
    for i,im in enumerate(frames):
        q=np.array(im);changed=np.any(p!=q,axis=2)
        diff=np.zeros_like(q);diff[changed]=[255,60,160,255]
        Image.fromarray(diff).save(OUT/f"cardinal-{i+1:02d}-difference.png")
        bbox=im.getchannel("A").getbbox()
        checks={"rgba192x208":im.mode=="RGBA" and im.size==(192,208),
                "bodyFromY61Identical":bool(np.array_equal(p[61:],q[61:])),
                "handsAndCollarIdentical":bool(np.array_equal(p[protected],q[protected])),
                "baseline203":bbox[3]-1==203,"fullFigureBboxUnchanged":bbox==idle.getbbox(),
                "binaryAlpha":set(np.unique(q[:,:,3]))=={0,255},
                "transparentRGBZero":not bool(q[q[:,:,3]==0,:3].any()),
                "oneConnectedFigure":len(components(im))==1}
        report["frames"].append({"direction":[0,90,180,270][i],"bbox":bbox,
                                  "changedPixels":int(changed.sum()),"checks":checks,
                                  "componentSizes":components(im)})
    report["structuralChecksPassed"]=all(all(f["checks"].values()) for f in report["frames"])
    (OUT/"validation.json").write_text(json.dumps(report,indent=2)+"\n")
    (OUT/"index.html").write_text('''<!doctype html><meta charset="utf-8"><title>Feng Look R6 · Gu 动作参考</title>
<style>body{background:#24272d;color:#eee;font:16px system-ui;margin:24px;line-height:1.6}img{image-rendering:pixelated;max-width:100%}a{color:#9dd7ff}.row{display:flex;gap:20px;flex-wrap:wrap}.note{max-width:1000px}</style>
<h1>Feng Look R6 — 四方向关键姿态，等待审核</h1>
<p class="note">Gu 只提供抬头、右转、低头、左转的动作参考，不借用 Gu 的脸和体型。身体、双手、手肘、袖口和西装来自正式 Feng Idle 的原始像素。头部由内置图像编辑生成，以统一的头部 X/Y 最近邻归一化匹配 Idle 尺度，再使用原头部调色板。不是未经修改的原头部像素；人物身份仍须人工审核。</p>
<p class="note">本页只有四张主要方向，不是完成的 16 帧连续动画。先检查外形和转头方式，未生成中间方向，未接入 App。</p>
<h2>左：Feng Idle · 中：Gu 动作参考 · 右：Feng 候选</h2><img src="gu-reference-preview.gif">
<div class="row"><div><h2>四方向轮播</h2><img src="cardinals-preview.gif"></div><div><h2>头部、手指和领口</h2><img src="head-and-hand.gif"></div></div>
<h2>Idle 与四方向原尺寸对照</h2><img src="idle-comparison.png">
<h2>放大检查</h2><img src="head-detail.png">
<p><a href="validation.json">结构校验（不等于美术批准）</a> · <a href="prompt.txt">首次编辑提示词</a> · <a href="head-only-prompt.txt">头部清理提示词</a></p>''',encoding="utf-8")
    return report


if __name__=="__main__":
    print(json.dumps(review(clean_head_candidates()),indent=2))
