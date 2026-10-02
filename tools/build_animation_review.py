#!/usr/bin/env python3
"""Build a read-only, source-labeled GIF review of standalone pet motions."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / ".cache/frame-review-2026-10-02"
CELL = (192, 208)
ATLAS = (1536, 2288)
BACKGROUND = (35, 38, 44)

# Must match standalone-app/animation.mjs. Cardinal anchors are included in look-16.
MOTIONS = (
    ("idle", "Idle / 待机", 0, [280, 110, 110, 140, 140, 320]),
    ("running-right", "Drag Right / 向右拖拽", 1, [120] * 7 + [220]),
    ("running-left", "Drag Left / 向左拖拽", 2, [120] * 7 + [220]),
    ("waving", "Waving / 挥手", 3, [140] * 3 + [280]),
    ("jumping", "Hover / Jumping", 4, [140] * 4 + [280]),
    ("failed", "Failed / 失败", 5, [140] * 7 + [240]),
    ("waiting", "Waiting / 等待", 6, [150] * 5 + [260]),
    ("running", "Running / 工作中", 7, [120] * 5 + [220]),
    ("review", "Review / 审查", 8, [150] * 5 + [280]),
)

TRIGGERS = {
    "idle": "默认；Stop/超时后恢复",
    "running-right": "实体鼠标向右拖拽",
    "running-left": "实体鼠标向左拖拽",
    "waving": "素材存在；当前 Desktop Hook／菜单无触发入口",
    "jumping": "鼠标 Hover",
    "failed": "素材存在；当前 Desktop Hook／菜单无触发入口",
    "waiting": "右键菜单可选；PermissionRequest 尚未接入",
    "running": "已验证的 PreToolUse；右键菜单亦可选",
    "review": "右键菜单可选；当前 Hook 未自动映射",
    "look-16": "Idle 时鼠标方向；000/090/180/270 为其中四帧",
    "gu-to-feng": "北京时间切换／右键 Form；当前运行 10 帧",
    "feng-to-gu": "北京时间切换／右键 Form；当前运行 8 帧",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def open_rgba(path: Path) -> Image.Image:
    with Image.open(path) as image:
        return image.convert("RGBA")


def cell(atlas: Image.Image, row: int, column: int) -> Image.Image:
    x, y = column * CELL[0], row * CELL[1]
    frame = atlas.crop((x, y, x + CELL[0], y + CELL[1]))
    if frame.getchannel("A").getbbox() is None:
        raise ValueError(f"empty atlas cell row={row} column={column}")
    return frame


def _opaque_preview(frame: Image.Image, size: tuple[int, int]) -> Image.Image:
    if frame.size != size:
        frame = frame.resize(size, Image.Resampling.NEAREST)
    canvas = Image.new("RGB", size, BACKGROUND)
    canvas.paste(frame, (0, 0), frame.getchannel("A"))
    return canvas


def save_preview(frames: list[Image.Image], durations: list[int], output: Path,
                 *, display_size: tuple[int, int] = (384, 416)) -> None:
    if not frames or len(frames) != len(durations):
        raise ValueError("preview frames/durations mismatch")
    output.parent.mkdir(parents=True, exist_ok=True)
    opaque = []
    for index, frame in enumerate(frames):
        preview = _opaque_preview(frame, display_size)
        # A review GIF must retain even byte-identical adjacent source frames.
        # Pillow/GIF otherwise merges them and hides an important motion defect.
        draw = ImageDraw.Draw(preview)
        draw.rectangle((4, 4, 37, 23), fill=(17, 19, 23))
        draw.text((8, 7), f"{index + 1:02d}", fill=(255, 255, 255))
        opaque.append(preview)
    palette_sample = Image.new("RGB", (display_size[0], display_size[1] * len(opaque)))
    for index, frame in enumerate(opaque):
        palette_sample.paste(frame, (0, index * display_size[1]))
    palette = palette_sample.quantize(colors=256, method=Image.Quantize.MEDIANCUT,
                                      dither=Image.Dither.NONE)
    indexed = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in opaque]
    indexed[0].save(output, save_all=True, append_images=indexed[1:],
                    duration=durations, loop=0, disposal=2, optimize=False)


def save_contact(frames: list[Image.Image], output: Path, *, columns: int = 8) -> None:
    panel_width, panel_height = 200, 230
    rows = (len(frames) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * panel_width, rows * panel_height), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    for index, frame in enumerate(frames):
        x, y = (index % columns) * panel_width, (index // columns) * panel_height
        preview = _opaque_preview(frame, (192, 208))
        sheet.paste(preview, (x + 4, y + 4))
        draw.text((x + 5, y + 214), f"{index + 1:02d}", fill=(235, 235, 235))
    sheet.save(output)


def record(output: Path, label: str, frames: list[Image.Image], durations: list[int],
           source: Path | list[Path], *, display_size: tuple[int, int] = (384, 416),
           status: str) -> dict:
    gif = output / f"{label}.gif"
    contact = output / f"{label}-frames.png"
    save_preview(frames, durations, gif, display_size=display_size)
    save_contact(frames, contact)
    sources = source if isinstance(source, list) else [source]
    pixel_hashes = [hashlib.sha256(frame.tobytes()).hexdigest() for frame in frames]
    return {
        "gif": gif.name, "contact": contact.name, "frames": len(frames),
        "uniquePixelFrames": len(set(pixel_hashes)),
        "adjacentIdenticalPairs": [index + 1 for index in range(len(frames) - 1)
                                   if pixel_hashes[index] == pixel_hashes[index + 1]],
        "status": status,
        "sources": [{"path": str(path.relative_to(ROOT)), "sha256": sha256(path)} for path in sources],
    }


def source_strip(path: Path, count: int) -> list[Image.Image]:
    image = open_rgba(path)
    if image.height != CELL[1] or image.width != CELL[0] * count:
        raise ValueError(f"unexpected strip dimensions: {path} {image.size}")
    return [image.crop((index * CELL[0], 0, (index + 1) * CELL[0], CELL[1]))
            for index in range(count)]


def candidate_images(folder: Path, stem: str, count: int, start: int) -> tuple[list[Image.Image], list[Path]]:
    paths = [folder / f"{stem}_{index:02d}.png" for index in range(start, start + count)]
    frames = [open_rgba(path) for path in paths]
    if any(frame.getchannel("A").getbbox() is None for frame in frames):
        raise ValueError(f"empty candidate frame: {folder}")
    return frames, paths


def review_page(output: Path, catalog: dict) -> None:
    bundle_note = (
        "旧打包 App 的隔离触发探针已观察到 Gu→Feng 的 0–9 帧与 Feng→Gu 的 0–7 帧，"
        "均切换到目标形态：<a href=\"bundled-trigger.json\">触发记录</a>。"
        "这仅证明触发及帧序，不证明过渡画面质量；完整窗口截图来自当前源码版本。"
        if (output / "bundled-trigger.json").is_file()
        else "旧打包 App 的触发探针尚未运行；完整窗口截图仅来自当前源码版本。"
    )
    def link(entry: dict | None, title: str = "") -> str:
        if not entry:
            return "—"
        gif = html.escape(entry["gif"])
        contact = html.escape(entry["contact"])
        caption = html.escape(title or f'{entry["frames"]} 帧')
        distinct = f'{entry["uniquePixelFrames"]}/{entry["frames"]} 不同像素帧'
        source = entry["sources"][0]["path"]
        original = f"../../{html.escape(source, quote=True)}"
        return (f'<figure><img src="{gif}" alt="{caption}">'
                f'<figcaption>{caption} · {distinct} · <a href="{gif}">GIF</a> · '
                f'<a href="{contact}">逐帧图</a> · '
                f'<a href="{original}">来源</a></figcaption></figure>')

    rows = []
    for slug, title, *_ in MOTIONS:
        candidate = []
        if slug in ("failed", "waiting"):
            candidate.append(link(catalog["candidates"].get(f"gu-eye-{slug}"), "Gu 眼部修复候选；未接入"))
        if slug == "running-right":
            candidate.append(link(catalog["candidates"].get("gu-drag-motion-reference"),
                                  "Gu 四姿势原图参考；非运行帧"))
        rows.append((title, link(catalog["app"]["gu"][slug], "Gu 当前运行"),
                     link(catalog["app"]["feng"][slug], "Feng 当前运行"),
                     "".join(candidate) or "—", TRIGGERS[slug]))
    rows.append(("Look / 16 方向", link(catalog["app"]["gu"]["look-16"], "Gu 当前运行"),
                 link(catalog["app"]["feng"]["look-16"], "Feng 当前运行"),
                 "—", TRIGGERS["look-16"]))
    rows.append(("Gu → Feng 变身", link(catalog["app"]["gu-to-feng"], "当前运行素材 · 10 帧")
                 + link(catalog["app"].get("gu-to-feng-window"), "隔离 App 实际窗口 · 10 帧"), "—",
                 link(catalog["candidates"].get("gu-to-feng-redraw"), "重绘草案 · VISUAL_QA_FAIL")
                 + link(catalog["candidates"].get("gu-to-feng-historical-1"), "历史试作 1 · 未接入")
                 + link(catalog["candidates"].get("gu-to-feng-historical-2"), "历史试作 2 · 未接入"),
                 TRIGGERS["gu-to-feng"]))
    rows.append(("Feng → Gu 变身", "—", link(catalog["app"]["feng-to-gu"], "当前运行素材 · 8 帧")
                 + link(catalog["app"].get("feng-to-gu-window"), "隔离 App 实际窗口 · 8 帧"),
                 "—", TRIGGERS["feng-to-gu"]))
    body = "\n".join("<tr>" + "".join(f"<td>{part}</td>" for part in row) + "</tr>" for row in rows)
    page = f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>Liang no Henshin · 全动作 GIF 审阅</title>
<style>body{{background:#17191d;color:#eee;font:14px system-ui;margin:24px}}
h1{{margin-bottom:4px}}p{{line-height:1.55;max-width:1100px}}
table{{border-collapse:collapse;min-width:1400px}}th,td{{vertical-align:top;border:1px solid #474b52;padding:10px}}
th{{position:sticky;top:0;background:#272a30}}td:first-child{{min-width:150px;font-weight:700}}
figure{{margin:0 8px 12px 0;display:inline-block}}img{{width:192px;height:auto;image-rendering:pixelated;background:#23262c}}
figcaption{{max-width:220px;font-size:12px;margin-top:3px}}a{{color:#9fc9ff}}</style></head><body>
<h1>全动作 GIF 审阅</h1>
<p>同一个动作占一行。左侧两列是独立 App 实际读取的正式图集／变身帧；右列是后续制作但未接入的候选。
GIF 为审阅用深色底、最近邻放大和调色板编码，不能用作生产素材。点击“逐帧图”查看每个动作的全部帧。</p>
<p>GIF 持续循环仅方便审阅，不表示运行时会无限循环。Look 16 方向 GIF 是按角度顺序制作的审阅扫描，
运行时由鼠标方向选定单帧。两张正式图集和变身清单与现有打包 App 的对应文件哈希一致；
“隔离 App 实际窗口”截图来自当前项目源码的测试运行，不代表旧打包 App 已通过相同测试。</p>
<p><strong>制作完成 ≠ 自动可触发 ≠ 视觉已通过。</strong> 挥手、失败目前没有 Desktop Hook 或菜单入口；
等待与审查仅可通过菜单设置；后续候选均未替换当前 App。Gu 拖拽源图只获动作参考批准，
不满足 192×208 / 硬边 / Idle 身份门禁。重绘的 Gu→Feng 草案已判 VISUAL_QA_FAIL。</p>
<p>{bundle_note}</p>
<table><thead><tr><th>动作</th><th>App 当前 Gu</th><th>App 当前 Feng</th><th>后续候选／历史试作</th><th>触发与备注</th></tr></thead><tbody>{body}</tbody></table>
<p>资源哈希、帧数及来源：<a href="inventory.json">inventory.json</a>。</p></body></html>"""
    (output / "index.html").write_text(page, encoding="utf-8")


def build(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    catalog: dict = {"app": {"gu": {}, "feng": {}}, "candidates": {}}
    for form in ("gu", "feng"):
        atlas_path = ROOT / f"assets/builds/{form}/spritesheet.webp"
        atlas = open_rgba(atlas_path)
        if atlas.size != ATLAS:
            raise ValueError(f"unexpected atlas size: {atlas_path} {atlas.size}")
        for slug, _title, row, durations in MOTIONS:
            frames = [cell(atlas, row, index) for index in range(len(durations))]
            catalog["app"][form][slug] = record(output, f"app-{form}-{slug}", frames,
                durations, atlas_path, status="CURRENT_APP")
        look = [cell(atlas, 9 + index // 8, index % 8) for index in range(16)]
        catalog["app"][form]["look-16"] = record(output, f"app-{form}-look-16", look,
            [180] * 16, atlas_path, status="CURRENT_APP")

    for direction, count, size in (("gu_to_feng", 10, (224, 240)),
                                   ("feng_to_gu", 8, (208, 224))):
        frames, paths = candidate_images(ROOT / "assets/transform-overlay" / direction,
                                         direction, count, 1)
        if any(frame.size != size for frame in frames):
            raise ValueError(f"unexpected overlay canvas: {direction}")
        catalog["app"][direction.replace("_", "-")] = record(output,
            f"app-{direction.replace('_', '-')}", frames, [140] * count, paths,
            status="CURRENT_APP", display_size=(size[0] * 2, size[1] * 2))
        captured = [output / "runtime-qa" / f"{direction}-{index:02d}.png"
                    for index in range(count)]
        if all(path.is_file() for path in captured):
            window_frames = [open_rgba(path) for path in captured]
            catalog["app"][f"{direction.replace('_', '-')}-window"] = record(output,
                f"live-window-{direction.replace('_', '-')}", window_frames,
                [140] * count, captured, status="ISOLATED_APP_RENDERER_CAPTURE",
                display_size=(512, 512))

    eye_folder = ROOT / "assets/rework/v0.1.0/gu-eye-repair-2026-10-01"
    for slug, count in (("failed", 8), ("waiting", 6)):
        path = eye_folder / f"{slug}.png"
        frames = source_strip(path, count)
        durations = [140] * 7 + [240] if slug == "failed" else [150] * 5 + [260]
        catalog["candidates"][f"gu-eye-{slug}"] = record(output,
            f"candidate-gu-eye-{slug}", frames, durations,
            path, status="CANDIDATE_REQUIRES_USER_VISUAL_REVIEW")

    raw = ROOT / "assets/rework/v0.1.0/gu-drag-side-shuffle-keyposes-2026-10-01/source-preview.png"
    source = open_rgba(raw)
    if source.size != (2172, 724):
        raise ValueError(f"motion reference dimensions changed: {source.size}")
    quarter = source.width // 4
    poses = [source.crop((index * quarter, 0, (index + 1) * quarter, source.height))
             for index in range(4)]
    catalog["candidates"]["gu-drag-motion-reference"] = record(output,
        "candidate-gu-drag-motion-reference", poses, [250] * 4, raw,
        status="MOTION_REFERENCE_ONLY_TECHNICAL_GATE_FAIL", display_size=(272, 362))

    redraw = ROOT / "assets/rework/v0.1.0/gu-to-feng-idle-redraw-2026-10-01/frames"
    frames, paths = candidate_images(redraw, "gu_to_feng", 10, 1)
    catalog["candidates"]["gu-to-feng-redraw"] = record(output,
        "candidate-gu-to-feng-redraw", frames, [180] * 10, paths,
        status="VISUAL_QA_FAIL", display_size=(355, 444))
    for index, folder in enumerate(("gu-to-feng", "gu-to-feng-retry"), start=1):
        path = ROOT / "assets/rework/v0.1.0/transition-full" / folder / "frames"
        frames, paths = candidate_images(path, "gu_to_feng", 10, 0)
        catalog["candidates"][f"gu-to-feng-historical-{index}"] = record(output,
            f"historical-gu-to-feng-{index}", frames, [140] * 10, paths,
            status="HISTORICAL_NOT_IN_APP")

    review_page(output, catalog)
    (output / "inventory.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2),
                                           encoding="utf-8")
    return catalog


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    catalog = build(args.output.resolve())
    app_count = len(catalog["app"]["gu"]) + len(catalog["app"]["feng"]) + 2
    app_count += int("gu-to-feng-window" in catalog["app"])
    app_count += int("feng-to-gu-window" in catalog["app"])
    print(f"REVIEW_READY {args.output.resolve() / 'index.html'} "
          f"app={app_count} "
          f"candidates={len(catalog['candidates'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
