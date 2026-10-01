# 素材冻结清单 — liang-no-henshin

冻结日期：2026-09-08

以下为已批准素材的最终目录与命名。冻结后不修改图片像素；后续如需校验文件未被改动，执行：

```bash
shasum -a 256 -c assets-frozen.sha256
```

## 角色状态素材

| 文件 | 角色 | 状态 |
| --- | --- | --- |
| assets/gu/idle.png | 梁文谷 idle | 已批准 |
| assets/gu/hover.png | 梁文谷 hover | 已批准 |
| assets/gu/drag.png | 梁文谷 drag | 已批准 |
| assets/feng/idle.png | 梁文峰 idle | 已批准 |
| assets/feng/hover.png | 梁文峰 hover | 已批准 |
| assets/feng/drag.png | 梁文峰 drag | 已批准 |

## gu_to_feng（梁文谷 → 梁文峰，最终播放顺序，10 帧）

| 文件 | 对应内容 |
| --- | --- |
| assets/transform/gu_to_feng/gu_to_feng_01.png | 原 Frame 1 |
| assets/transform/gu_to_feng/gu_to_feng_02.png | 原 Frame 2 |
| assets/transform/gu_to_feng/gu_to_feng_03.png | 原 Frame 3 |
| assets/transform/gu_to_feng/gu_to_feng_04.png | 原 Frame 6 |
| assets/transform/gu_to_feng/gu_to_feng_05.png | 原 Frame 4 |
| assets/transform/gu_to_feng/gu_to_feng_06.png | Transition A |
| assets/transform/gu_to_feng/gu_to_feng_07.png | 原 Frame 5 |
| assets/transform/gu_to_feng/gu_to_feng_08.png | Transition B |
| assets/transform/gu_to_feng/gu_to_feng_09.png | 原 Frame 7 |
| assets/transform/gu_to_feng/gu_to_feng_10.png | 原 Frame 8 |

## feng_to_gu（梁文峰 → 梁文谷，最终播放顺序，8 帧）

| 文件 | 对应内容 |
| --- | --- |
| assets/transform/feng_to_gu/feng_to_gu_01.png | 原 Frame 1 |
| assets/transform/feng_to_gu/feng_to_gu_02.png | 原 Frame 2 |
| assets/transform/feng_to_gu/feng_to_gu_03.png | 原 Frame 3 |
| assets/transform/feng_to_gu/feng_to_gu_04.png | Transition C |
| assets/transform/feng_to_gu/feng_to_gu_05.png | 原 Frame 4 |
| assets/transform/feng_to_gu/feng_to_gu_06.png | 原 Frame 5 |
| assets/transform/feng_to_gu/feng_to_gu_07.png | 原 Frame 6 |
| assets/transform/feng_to_gu/feng_to_gu_08.png | 原 Frame 7 |

说明：`feng_to_gu` 目录原保存为 `feng_tu_gu_*.png`，本轮仅按统一命名重命名为 `feng_to_gu_*.png`，未改动图片内容。

范围外：`pic/` 下两张既有 PNG 与本轮批准素材无关，未纳入冻结。

## 2026-10-01 用户确认：保留 Feng → Gu，重绘 Gu → Feng

- 用户明确满意上一版 Feng → Gu **8 帧**，后续不再修改。冻结包括 `assets/transform-overlay/feng_to_gu/` 中实际运行的八张 PNG 及 `assets/transform/feng_to_gu/` 中的对应原始素材。没有新的明确授权时，不重绘、缩放、重排或覆盖它们。
- 对应 SHA256 固定记录在 `docs/transition-redraw/v0.1.0/feng-to-gu-approved-2026-10-01.json`。
- Gu → Feng 另行重绘，沿用 **10 个变身动作帧**；Gu Idle 与 Feng Idle 仅作前后参照，均不计入十帧，不以复制 Idle 补足数量。
- 新稿的画风、脸部身份、头身比、西装结构均以 `assets/gu/idle.png`、`assets/feng/idle.png` 和正式 atlas 的 Idle 为准。旧 E1/E2/E3 不作新稿的形体参考。
- 新稿保存为独立候选，视觉审批与运行素材替换分开；现有 Gu/Feng 标准 atlas 和已运行素材保留。
- 同日用户追加不可放宽的“Idle 完全一致”要求；执行 `docs/transition-redraw/v0.1.0/strict-idle-appearance-contract.md` 与实际 Idle 像素指标。所有未知/失败项都阻止批准，不得用“风格接近”或纯 bbox PASS 代替。

## 2026-10-01 用户追加：所有动画候选必须附 GIF 审阅

- 后续每一版动画候选均提供原顺序 GIF、逐帧图及帧数/时长说明，再交用户人工审核。
- 预览对齐、统一 nearest-neighbor 展示缩放、GIF 配色及背景限制必须注明；如做对齐，同时提供原位置版本。
- 不以静态图、自动化检查或“继续”代替视觉批准，不为掩盖缺陷而省帧、插帧或加速。
- 具体执行规则：`.cursor/rules/animation-visual-review.mdc`。
