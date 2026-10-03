"""Feng Look R3: keep complete original head/hand; repair only outer shoulders."""
from pathlib import Path
import sys,json,hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageFilter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.repair_reviewed_actions import frame,skin_mask,difference
from tools.rework_action_candidates import clean_edge
from tools.build_animation_review import save_preview,save_contact

OUT=ROOT/"assets/rework/v0.1.0/feng-look-r3-2026-10-04"
SOURCE=ROOT/"assets/builds/feng/spritesheet.webp"


def repair(source,donor):
    pixels=np.array(source)
    # The central channel contains the WHOLE hand, cuff, wrist, neck and face.
    # Never use a skin-derived head mask or cut across that channel.
    mask=np.zeros((208,192),bool)
    mask[62:94,:62]=True
    mask[62:94,115:]=True
    protected=np.array(Image.fromarray(skin_mask(source).astype(np.uint8)*255).filter(ImageFilter.MaxFilter(5)))>0
    mask &= ~protected
    pixels[mask]=np.array(donor)[mask]
    coherent=Image.fromarray(pixels)
    cleaned,_=clean_edge(coherent)
    # White-edge cleanup must not alter any original hand/cuff pixel either.
    clean=np.array(cleaned)
    clean[44:108,62:115]=pixels[44:108,62:115]
    return Image.fromarray(clean),Image.fromarray(mask.astype(np.uint8)*255)


def sheets(groups,labels,roi,path,start_index=0):
    w,h=(roi[2]-roi[0])*3,(roi[3]-roi[1])*3
    rows=len(groups[0]);board=Image.new("RGB",(w*len(groups),(h+22)*rows),(64,28,65))
    d=ImageDraw.Draw(board)
    for col,(items,label) in enumerate(zip(groups,labels)):
        for i,im in enumerate(items):
            crop=im.crop(roi).resize((w,h),Image.Resampling.NEAREST)
            x,y=col*w,i*(h+22)
            board.paste(crop,(x,y+22),crop.getchannel("A"));d.text((x+3,y+3),f"{start_index+i+1:02d} {label}",fill="white")
    board.save(path)


def build():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/"review-status.json").exists():raise RuntimeError("reviewed output locked")
    sha=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    atlas=Image.open(SOURCE).convert("RGBA")
    raw=[frame(atlas,9+i//8,i%8) for i in range(16)]
    prior=Image.open(ROOT/"assets/rework/v0.1.0/action-repair-2026-10-02/feng.webp").convert("RGBA")
    rejected=[frame(prior,9+i//8,i%8) for i in range(16)]
    result=[];rows=[]
    for i,source in enumerate(raw):
        im,mask=repair(source,raw[0]);result.append(im)
        im.save(OUT/f"{i+1:02d}.png");mask.save(OUT/f"{i+1:02d}-shoulder-mask.png")
        diff,n=difference(source,im);diff.save(OUT/f"{i+1:02d}-difference.png")
        roi=(62,44,115,108)
        same=source.crop(roi).tobytes()==im.crop(roi).tobytes()
        assert same
        rows.append({"frame":i+1,"direction":i*22.5,"changedPixels":n,
                     "fullHandCuffChannelPixelIdentical":same,"bbox":im.getchannel("A").getbbox()})
    for half in range(2):
        strip=Image.new("RGBA",(1536,208))
        for i in range(8):strip.paste(result[half*8+i],(i*192,0))
        strip.save(OUT/f"look-row-{9+half}.png")
    save_contact(result,OUT/"contact.png")
    save_preview(result,[180]*16,OUT/"preview.gif")
    save_preview(result,[500]*16,OUT/"preview-slow.gif")
    save_preview(raw,[180]*16,OUT/"original.gif")
    save_preview(rejected,[180]*16,OUT/"rejected-r1.gif")
    for begin in range(0,16,4):
        sheets([raw[begin:begin+4],rejected[begin:begin+4],result[begin:begin+4]],
               ["ORIGINAL","REJECTED R1","R3"],(38,40,154,111),OUT/f"compare-{begin+1:02d}-{begin+4:02d}.png",begin)
    sheets([result],["R3 full hand"],(62,44,115,108),OUT/"all-hands.png")
    sheets([[result[15]],[result[0]]],["16 / 337.5","01 / 000"],(38,0,154,208),OUT/"loop-16-to-01.png")
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==sha
    report={"status":"SELF_REVIEW_PENDING","runtimeIntegrated":False,"sourceSha256":sha,
            "source":str(SOURCE.relative_to(ROOT)),"frames":rows,
            "method":"Original direction head, hand, cuff and central torso retained; only outer shoulders copied from original Up; constrained exterior cleanup",
            "protectedRectangle":[62,44,115,108],"dynamicPlayback":"NOT_VERIFIED"}
    (OUT/"validation.json").write_text(json.dumps(report,indent=2)+"\n")
    comparisons="".join(f'<h3>帧 {b+1:02d}–{b+4:02d}：原图 / 旧版失败 / R3</h3><img src="compare-{b+1:02d}-{b+4:02d}.png">' for b in range(0,16,4))
    (OUT/"index.html").write_text('''<!doctype html><meta charset="utf-8"><title>Feng Look R3 审阅</title>
<style>body{background:#26292f;color:#eee;font:16px system-ui;margin:24px}img{image-rendering:pixelated;max-width:100%}.gif{width:384px}section{display:flex;gap:30px;flex-wrap:wrap}a{color:#9dd7ff}</style>
<h1>Feng Look R3 · 仅候选，尚未接入 App</h1>
<p>保留原方向帧完整头颈、手掌、手腕和袖口；只统一外侧肩部并清理外缘。不是重新绘制头部。</p>
<p>16 帧静态自检与字节保护检查；动态播放仍须审阅。不代表用户批准或真机通过。</p>
<section><div><h2>正常预览 · 180ms/帧</h2><img class="gif" src="preview.gif"></div><div><h2>慢速预览 · 500ms/帧</h2><img class="gif" src="preview-slow.gif"></div></section>
<h2>全部 16 方向</h2><img src="contact.png">'''+comparisons+'''<h2>循环边界 16→1</h2><img src="loop-16-to-01.png"><p><a href="validation.json">机器校验</a></p>''',encoding="utf-8")
    return result


if __name__=="__main__":build()
