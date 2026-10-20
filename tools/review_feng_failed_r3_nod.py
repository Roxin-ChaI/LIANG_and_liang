"""Review-only stronger nod revision, preserving the first trial and fixed fists."""
from pathlib import Path
import json
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.prepare_feng_failed_r3 import OUT as BASE
from tools.finish_feng_failed_r3 import build, masks, DURATIONS
from tools.build_animation_review import cell, save_preview

OUT = BASE / "nod-revision"


def review():
    report = build(output=OUT, upper_source=OUT/"source-upper-edit.png",
                   lock_head_silhouette=True)
    idle = Image.open(BASE/"canonical-idle.png").convert("RGBA")
    p = np.array(idle)
    head, raised, lower = masks(idle)
    canonical_box = Image.fromarray(((p[:,:,3]>0)&head).astype(np.uint8)*255).getbbox()
    for i, item in enumerate(report["frames"]):
        q = np.array(Image.open(OUT/f"failed-{i+1:02d}.png"))
        box = Image.fromarray(((q[:,:,3]>0)&head).astype(np.uint8)*255).getbbox()
        item["headBbox"] = box
        item["headSize"] = [box[2]-box[0],box[3]-box[1]]
        item["headCenter"] = [(box[0]+box[2]-1)/2,(box[1]+box[3]-1)/2]
        item["checks"]["headFootprintMatchesIdle"] = box == canonical_box
        item["checks"]["raisedWristOriginal"] = bool(np.array_equal(q[77:81,72:92],p[77:81,72:92]))
        item["checks"]["lowerWristOriginal"] = bool(np.array_equal(q[130:136,126:147],p[130:136,126:147]))
    report["structuralChecksPassed"] = all(all(f["checks"].values()) for f in report["frames"])
    report["status"] = "CANDIDATE_READY_FOR_USER_REVIEW"
    report["selfReview"] = {
        "scope": "Native + 4x ordered frames + 6x hands/cuffs, not App runtime QA",
        "userApproval": "PENDING",
        "observations": [
            "Clearer downward facial pitch than the rejected first trial",
            "No visible duplicate finger, detached wrist, elbow or lapel tearing in reviewed sheets",
            "Same fixed fist pixels during frames 2-7; original pointing/resting hands at 1/8",
            "Head outer footprint restored from Idle; facial planes change inside it",
        ],
        "limitations": [
            "Generated local facial art is not pixel-identical to the original face",
            "Automated geometric checks cannot certify perceived identity or motion quality",
            "No user approval or live App integration is claimed",
        ],
    }
    gu = Image.open(ROOT/"assets/rework/v0.1.0/action-repair-2026-10-02/gu.webp").convert("RGBA")
    comparisons = []
    for i in range(8):
        im = Image.open(OUT/f"failed-{i+1:02d}.png").convert("RGBA")
        panel=Image.new("RGBA",(576,232));d=ImageDraw.Draw(panel)
        for col,(sprite,title) in enumerate([(idle,"FENG IDLE / LOCKED"),
                                           (cell(gu,5,i),"GU FAILED / MOTION"),
                                           (im,"FENG FAILED / CANDIDATE")]):
            panel.paste(sprite,(col*192,24));d.text((col*192+4,4),title,fill="white")
        comparisons.append(panel)
    save_preview(comparisons,DURATIONS,OUT/"reference-comparison.gif",display_size=(1152,464))
    # A supplemental hand-only sheet catches cuff cuts hidden at native scale.
    board=Image.new("RGB",(9*180,520),(48,34,46));d=ImageDraw.Draw(board)
    sprites=[idle]+[Image.open(OUT/f"failed-{i:02d}.png").convert("RGBA") for i in range(1,9)]
    for i,sprite in enumerate(sprites):
        d.text((i*180+6,5),"IDLE" if i==0 else f"{i:02d}",fill="white")
        for y,box in [(30,(72,48,98,83)),(320,(126,128,148,154))]:
            patch=sprite.crop(box);patch=patch.resize((patch.width*6,patch.height*6),Image.Resampling.NEAREST)
            board.paste(patch,(i*180+4,y),patch.getchannel("A"))
    board.save(OUT/"hands-and-cuffs.png")
    (OUT/"validation.json").write_text(json.dumps(report,indent=2)+"\n")
    (OUT/"index.html").write_text("""<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Feng Failed R3 — 低头与原位握拳</title>
<style>body{background:#24272d;color:#eee;font:16px system-ui;margin:24px;line-height:1.6}
img{max-width:100%;image-rendering:pixelated}a{color:#a5d6ff}section{margin:24px 0}</style>
<h1>Feng Failed · 8 帧候选，等待审核</h1>
<p>身体、袖口、手肘、领口、腿鞋使用正式 Feng Idle 原像素。只编辑头部与双手手指。
头部参考 Gu Failed 的停顿、低头、闭眼、恢复，不复制 Gu 的人物外观。
头部占位 49×57，脚底 y=203，手腕固定。第 1/8 帧为原 Idle，第 4/5 帧有意停顿。</p>
<p>局部内容使用内置 ImageGen 编辑，按原网格最近邻恢复并映射到 Idle 调色板；
头部轮廓锁定，不代表脸部像素完全相同。已检查静态顺序图，不代表用户美术批准或 App 验收。
正式图集与当前运行 App 均未替换。</p>
<section><h2>左：Feng Idle / 右：本次候选</h2><img src="idle-comparison.gif" alt="Idle 与 Failed 动作对照"></section>
<section><h2>正常速度</h2><img src="preview.gif" alt="八帧正常速度预览">
<h2>慢速逐帧</h2><img src="preview-slow.gif" alt="八帧慢速预览"></section>
<section><h2>Gu 动作参考对照</h2><img src="reference-comparison.gif" alt="Feng Idle、Gu Failed 参考、Feng Failed 候选"></section>
<section><h2>全部八帧</h2><img src="contact.png" alt="八帧全身图"></section>
<section><h2>头部、拳头、领口</h2><img src="head-hand-contact.png" alt="头手放大">
<img src="head-hand-preview.gif" alt="头手动态放大"></section>
<section><h2>手腕与袖口</h2><img src="hands-and-cuffs.png" alt="双手与袖口逐帧"></section>
<p><a href="validation.json">逐帧结构报告与自检范围</a> · <a href="feng-failed.png">RGBA 原尺寸条带</a></p>
</html>""",encoding="utf-8")
    return report


if __name__=="__main__":
    print(json.dumps(review(),indent=2))
