#!/usr/bin/env python3
"""Source-labeled original/selected GIF review. Does not edit source artwork."""
import html
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build_animation_review import MOTIONS, cell, save_contact, save_preview
from tools.repair_reviewed_actions import OUTPUT


def build():
    out = ROOT / ".cache/action-review-2026-10-03"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    catalog = []
    def item(label, frames, durations, source, size=(384,416)):
        save_preview(frames, durations, out / f"{label}.gif", display_size=size)
        save_contact(frames, out / f"{label}.png")
        catalog.append({"label": label, "source": source, "frames": len(frames), "durations": durations})
        return (f'<figure><img src="{label}.gif"><figcaption>{len(frames)} 帧 · '
                f'<a href="{label}.gif">GIF</a> · <a href="{label}.png">逐帧图</a><br>'
                f'<small>{html.escape(source)}</small></figcaption></figure>')
    for slug, title, row, lengths in MOTIONS:
        panels = []
        for form in ("gu", "feng"):
            for version in ("original", "selected"):
                source = ROOT / f"assets/builds/{form}/spritesheet.webp" if version == "original" else OUTPUT / f"{form}.webp"
                atlas = Image.open(source).convert("RGBA")
                timing = [120] * 8 if version == "selected" and row in (1,2) else lengths
                panels.append(item(f"{form}-{slug}-{version}", [cell(atlas,row,i) for i in range(len(lengths))],
                                   timing, str(source.relative_to(ROOT))))
        rows.append(f'<tr><th>{title}</th>'+''.join(f'<td>{p}</td>' for p in panels)+'</tr>')
    panels=[]
    for form in ("gu","feng"):
        for version in ("original","selected"):
            source=ROOT/f"assets/builds/{form}/spritesheet.webp" if version=="original" else OUTPUT/f"{form}.webp"
            atlas=Image.open(source).convert("RGBA")
            panels.append(item(f"{form}-look-{version}",[cell(atlas,9+i//8,i%8) for i in range(16)],
                               [180]*16,str(source.relative_to(ROOT))))
    rows.append('<tr><th>Look / 16 方向</th>'+''.join(f'<td>{p}</td>' for p in panels)+'</tr>')
    for direction,count in [("gu_to_feng",10),("feng_to_gu",8)]:
        panels=[]
        for version in ("original","selected"):
            folder=ROOT/f"assets/transform-overlay/{direction}"
            if direction=="gu_to_feng" and version=="selected": folder=OUTPUT/direction
            frames=[Image.open(folder/f"{direction}_{i:02d}.png").convert("RGBA") for i in range(1,count+1)]
            panels.append(item(f"{direction}-{version}",frames,[140]*count,str(folder.relative_to(ROOT)),
                               (frames[0].width*2,frames[0].height*2)))
        rows.append(f'<tr><th>{direction.replace("_", " ")}<br>{"历史试作 2" if count==10 else "已批准；未修改"}</th>'
                    f'<td colspan="2">{panels[0]}</td><td colspan="2">{panels[1]}</td></tr>')
    page='''<!doctype html><meta charset="utf-8"><title>动作修复审核 · 2026-10-03</title>
<style>body{background:#171a20;color:#e9edf1;font:15px system-ui;margin:24px}a{color:#91c8ff}
table{border-collapse:collapse;width:100%}td,th{border:1px solid #47505a;padding:8px;vertical-align:top}
th{min-width:110px}figure{margin:0}img{width:192px;height:auto;image-rendering:pixelated}
small{display:block;max-width:230px;overflow-wrap:anywhere;color:#9faabd}thead{position:sticky;top:0;background:#222832}
.note{background:#292f39;padding:15px;line-height:1.7}</style>
<h1>动作修复审核</h1><p class="note">每个动作一行；标准动作：Gu 原版 / Gu 修复 / Feng 原版 / Feng 修复。
GIF 为审阅用有背景预览；运行素材仍为 RGBA。拖拽原版每圈末帧 220ms，修复版全部 120ms，保留原 8 帧顺序。
动作姿势尚需人工审批，不代表视觉 QA 全部通过。Feng→Gu 未修改。Gu 四姿势参考未使用。<br>
Look 固定完整肩领/身体，只复制各方向头部；Failed/Waiting 使用已选 Gu 眼部候选。
Gu→Feng 使用用户指定历史试作 2，未重画/缩放。旧运行 App 没有被替换。<br>
<a href="../../assets/rework/v0.1.0/action-repair-2026-10-02/qa/">差异 mask 和肩部放大对照</a> ·
<a href="../action-repair-live-2026-10-03/report.json">真实 Electron 运行记录</a></p>
<table><thead><tr><th>动作</th><th>Gu 原版</th><th>Gu 修复</th><th>Feng 原版</th><th>Feng 修复</th></tr></thead><tbody>'''
    live = ROOT / ".cache/action-repair-bundled-2026-10-03"
    live_panels = []
    for direction, count in [("gu_to_feng",10),("feng_to_gu",8)]:
        paths = [live/f"{direction}-{i:02d}.png" for i in range(count)]
        if all(p.exists() for p in paths):
            frames = [Image.open(p).convert("RGBA") for p in paths]
            live_panels.append(item(f"live-{direction}", frames, [140]*count,
                                    "打包审核版实际窗口截图；GIF 使用配置 dwell，非时长测量", frames[0].size))
    (out/"index.html").write_text(page+''.join(rows)+'</tbody></table><h2>实际窗口逐帧截图预览</h2>'+''.join(live_panels))
    (out/"catalog.json").write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    print(out/"index.html")


if __name__=="__main__": build()
