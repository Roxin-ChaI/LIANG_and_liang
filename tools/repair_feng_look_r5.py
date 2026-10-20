"""Review-only Feng look, using a complete Idle body and a separate head layer."""
from pathlib import Path
import sys
import math
import json
import hashlib

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.repair_reviewed_actions import frame
from tools.build_animation_review import save_preview, save_contact

SOURCE = ROOT / "assets/builds/feng/spritesheet.webp"
OUT = ROOT / "assets/rework/v0.1.0/feng-look-r5-2026-10-20"


def masks(idle):
    """Explicit silhouette and foreground finger; never infer a head from skin."""
    head = np.zeros((208, 192), bool)
    head[:48] = True
    spans = [(74,108),(75,106),(76,105),(77,104),(78,103),(79,102),
             (80,101),(81,100),(82,99),(84,98),(86,97),(88,95),(89,93)]
    for y, (left, right) in enumerate(spans, 48):
        head[y,left:right] = True
    head &= np.array(idle)[:,:,3] > 0
    foreground = np.zeros((208,192),bool)
    fingers = {49:(85,88),50:(84,89),51:(83,90),52:(83,90),53:(83,90),
               54:(83,90),55:(83,90),56:(82,90),57:(82,90),58:(82,90),
               59:(81,91),60:(80,93)}
    for y,(left,right) in fingers.items():
        foreground[y,left:right] = True
    # Full lower palm, cuff, elbow and suit are one immutable body layer.
    foreground[61:] = True
    return head, foreground


def head_texture(idle, head, foreground):
    p=np.array(idle)
    # Restore only face pixels hidden behind the original finger. The original
    # finger is composited in front after the head changes direction.
    for y in range(49,60):
        for x in range(81,90):
            if head[y,x] and foreground[y,x]:
                p[y,x]=p[y,91]
    p[~head]=0
    return p


def make_frame(idle, angle):
    source=np.array(idle)
    head, foreground=masks(idle)
    texture=head_texture(idle,head,foreground)
    body=source.copy()
    body[head & ~foreground]=0
    # Opaque neck underlay is restricted to the old head silhouette. Existing
    # shirt, lapels, hand and body pixels can never be touched by this layer.
    for y in range(49,61):
        for x in range(79,108):
            if head[y,x] and not foreground[y,x]:
                body[y,x]=source[min(65,max(57,y)),min(101,max(93,x))]
    radians=math.radians(angle)
    yaw=math.sin(radians)
    pitch=-math.cos(radians)
    yy,xx=np.indices((208,192),dtype=float)

    def displacement(x,y):
        # A small rounded head surface. Ears and rear hair move less than the
        # nose/front face. Neck pivot remains at y=60, instead of translating
        # a rectangular crop. One nearest-neighbour lookup; no blended pixels.
        cross=np.clip(1-((x-89.5)/29.0)**2,0,1)
        pivot=np.clip((60-y)/12.0,0,1)
        face=np.clip((y-18)/18.0,0,1)
        dx=yaw*(0.7+3.0*cross*face)*pivot
        dy=pitch*1.7*cross*face*pivot + yaw*0.45*(x-89.5)/29.0*pivot
        return dx,dy

    sx,sy=xx.copy(),yy.copy()
    for _ in range(5):
        dx,dy=displacement(sx,sy)
        sx,sy=xx-dx,yy-dy
    sx=np.clip(np.rint(sx).astype(int),0,191)
    sy=np.clip(np.rint(sy).astype(int),0,207)
    turned=texture[sy,sx]
    mutable=(head | (source[:,:,3]==0)) & ~foreground
    mutable[61:]=False
    visible=(turned[:,:,3]>0) & mutable
    body[visible]=turned[visible]
    body[foreground]=source[foreground]
    body[body[:,:,3]==0]=0
    return Image.fromarray(body)


def semantic_head_bbox(idle, im):
    head,_=masks(idle)
    alpha=(np.array(im)[:,:,3]>0)&(head|(np.array(idle)[:,:,3]==0))
    alpha[61:]=False
    return Image.fromarray(alpha.astype(np.uint8)*255).getbbox()


def build():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/"review-status.json").exists():
        raise RuntimeError("Reviewed artwork is locked")
    idle=frame(Image.open(SOURCE).convert("RGBA"),0,0)
    frames=[make_frame(idle,i*22.5) for i in range(16)]
    head,foreground=masks(idle)
    Image.fromarray(head.astype(np.uint8)*255).save(OUT/"head-mask.png")
    Image.fromarray(foreground.astype(np.uint8)*255).save(OUT/"foreground-mask.png")
    Image.fromarray(head_texture(idle,head,foreground)).save(OUT/"head-texture.png")
    for i,im in enumerate(frames):
        im.save(OUT/f"{i+1:02d}.png")
        changed=np.any(np.array(im)!=np.array(idle),axis=2)
        diff=np.zeros((208,192,4),np.uint8)
        diff[changed]=[255,70,150,255]
        Image.fromarray(diff).save(OUT/f"{i+1:02d}-difference.png")
    for row in (9,10):
        strip=Image.new("RGBA",(1536,208))
        for i in range(8):strip.paste(frames[(row-9)*8+i],(192*i,0))
        strip.save(OUT/f"look-row-{row}.png")
    save_contact(frames,OUT/"contact.png")
    save_preview(frames,[180]*16,OUT/"preview.gif")
    save_preview(frames,[500]*16,OUT/"preview-slow.gif")
    save_preview([im.crop((56,0,121,90)) for im in frames],[300]*16,
                 OUT/"head-and-hand.gif",display_size=(390,540))
    board=Image.new("RGB",(400*4,500),(56,28,58))
    d=ImageDraw.Draw(board)
    for col,i in enumerate([0,4,8,12]):
        crop=frames[i].crop((50,0,130,94)).resize((400,470),Image.Resampling.NEAREST)
        board.paste(crop,(400*col,30),crop.getchannel("A"))
        d.text((col*400+8,8),f"{i+1:02d} / {i*22.5:g}",fill="white")
    board.save(OUT/"cardinals-detail.png")
    anchors=[idle]+[frames[i] for i in [0,4,8,12]]
    compare=Image.new("RGB",(192*5,236),(36,39,45))
    draw=ImageDraw.Draw(compare)
    for i,(im,label) in enumerate(zip(anchors,["CANONICAL IDLE","000 UP","090 RIGHT","180 DOWN","270 LEFT"])):
        compare.paste(im,(192*i,24),im.getchannel("A"))
        draw.text((192*i+5,5),label,fill="white")
    compare.save(OUT/"idle-comparison.png")
    loop=Image.new("RGB",(584,388),(56,28,58))
    draw=ImageDraw.Draw(loop)
    for col,i in enumerate([15,0]):
        crop=frames[i].crop((52,0,125,91)).resize((292,364),Image.Resampling.NEAREST)
        loop.paste(crop,(292*col,24),crop.getchannel("A"))
        draw.text((292*col+8,6),f"{i+1:02d} / {i*22.5:g}",fill="white")
    loop.save(OUT/"loop-16-to-01.png")
    for first in range(0,16,4):
        detail=Image.new("RGB",(1168,388),(56,28,58))
        draw=ImageDraw.Draw(detail)
        for k,im in enumerate(frames[first:first+4]):
            crop=im.crop((52,0,125,91)).resize((292,364),Image.Resampling.NEAREST)
            detail.paste(crop,(k*292,24),crop.getchannel("A"))
            draw.text((k*292+8,6),f"{first+k+1:02d} / {(first+k)*22.5:g}",fill="white")
        detail.save(OUT/f"detail-{first+1:02d}-{first+4:02d}.png")
    adjacent=[]
    for i,im in enumerate(frames):
        nxt=frames[(i+1)%16]
        overlay=Image.blend(im.convert("RGBA"),nxt.convert("RGBA"),0.5)
        # Blending is a diagnostic overlay only; runtime art is never blended.
        overlay.save(OUT/f"adjacent-{i+1:02d}-overlay.png")
        adjacent.append({"from":i+1,"to":(i+1)%16+1,
                         "changedPixels":int(np.any(np.array(im)!=np.array(nxt),axis=2).sum())})
    p=np.array(idle)
    report={"status":"CANDIDATE_AWAITING_VISUAL_REVIEW", "userApproval":"PENDING",
            "method":"Small nearest-neighbour deformation of approved Idle head pixels around the neck pivot; hand drawn in front from the original Idle layer",
            "imagegenUsed":False, "bodyRepainted":False,"runtimeIntegrated":False,
            "source":str(SOURCE.relative_to(ROOT)),"sourceSha256":hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            "frameSize":[192,208],"directions":[i*22.5 for i in range(16)],
            "distinctPixelFrames":len({im.tobytes() for im in frames}),
            "registrationX":96,"baselineY":203,
            "canonicalHeadBbox":semantic_head_bbox(idle,idle),
            "frames":[{"frame":i+1,"bbox":im.getchannel("A").getbbox(),
                       "bodyFromY61ByteIdentical":bool(np.array_equal(np.array(im)[61:],p[61:])),
                       "foregroundByteIdentical":bool(np.array_equal(np.array(im)[foreground],p[foreground])),
                       "headBbox":semantic_head_bbox(idle,im)}
                      for i,im in enumerate(frames)],
            "adjacent":adjacent,
            "dynamicPlaybackObserved":"NOT_VERIFIED"}
    (OUT/"validation.json").write_text(json.dumps(report,indent=2)+"\n")
    details=''.join(f'<h3>{i+1:02d}–{i+4:02d}</h3><img src="detail-{i+1:02d}-{i+4:02d}.png">' for i in range(0,16,4))
    (OUT/"index.html").write_text('''<!doctype html><meta charset="utf-8"><title>Feng Look R5 审阅</title>
<style>body{background:#26292f;color:#eee;font:16px system-ui;margin:24px}img{image-rendering:pixelated;max-width:100%}section{display:flex;gap:24px;flex-wrap:wrap}a{color:#9dd7ff}</style>
<h1>Feng Look R5 · 头部转向候选</h1>
<p>完整复用正式 Idle 身体、双手、手肘、袖口和西装；头部按颈部支点小幅转向，原手指始终覆盖在脸部前方。保持 192×208、基线 203 与原调色板。等待审核，未接入 App。</p>
<section><div><h2>正常速度</h2><img src="preview.gif"></div><div><h2>慢速</h2><img src="preview-slow.gif"></div><div><h2>头部与手指放大</h2><img src="head-and-hand.gif"></div></section>
<h2>与正式 Idle 对照</h2><img src="idle-comparison.png"><h2>四个主要方向</h2><img src="cardinals-detail.png"><h2>全部 16 帧</h2><img src="contact.png">'''+details+'''<h2>16→1</h2><img src="loop-16-to-01.png"><p><a href="validation.json">结构和逐帧差异报告</a></p>''',encoding="utf-8")
    return frames


def diagnose():
    OUT.mkdir(parents=True, exist_ok=True)
    idle = frame(Image.open(SOURCE).convert("RGBA"), 0, 0)
    idle.save(OUT / "canonical-idle.png")
    for name, box in [("face-grid", (65, 35, 116, 71)), ("arm-grid", (69, 45, 110, 93))]:
        crop = idle.crop(box)
        scale = 14
        board = Image.new("RGB", (crop.width*scale+40, crop.height*scale+30), (55, 25, 55))
        enlarged = crop.resize((crop.width*scale, crop.height*scale), Image.Resampling.NEAREST)
        board.paste(enlarged, (40, 30), enlarged.getchannel("A"))
        d = ImageDraw.Draw(board)
        for x in range(box[0], box[2]):
            if x%2 == 0:
                d.text((40+(x-box[0])*scale, 5), str(x), fill="white")
        for y in range(box[1], box[3]):
            d.text((2, 30+(y-box[1])*scale), str(y), fill="white")
        board.save(OUT / f"{name}.png")


if __name__ == "__main__":
    diagnose()
    build()
