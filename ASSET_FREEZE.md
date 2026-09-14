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
