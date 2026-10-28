# v0.1.1 Codex / DeepSeek Harness 桌宠素材导出

来源：已发布 `assets/releases/v0.1.1/{gu,feng}.webp`。
运行 `python tools/export_pet_formats.py`，输出 `dist/exports/v0.1.1/`；拒绝覆盖已有导出。

## 选择文件

| 用途 | ZIP 名称后缀 | 图集 | 包含动作 |
|---|---|---|---|
| 原生 Codex Pet v2 | `codex-v2-gu.zip` / `codex-v2-feng.zip` | 1536×2288，8×11 | 9 种动画 + 16 个 Look 方向 |
| 支持 Codex v2 的 DSH 桌宠插件 | `dsh-v2-gu.zip` / `dsh-v2-feng.zip` | 1536×2288，8×11 | 同上 |
| 只支持旧 9 行格式的 DSH 插件 | `dsh-v1-legacy-gu.zip` / `dsh-v1-legacy-feng.zip` | 1536×1872，8×9 | 9 种动画，不含 Look |

所有文件名前缀为 `LIANG_and_liang-v0.1.1-`。总包 `LIANG_and_liang-v0.1.1-pet-formats.zip` 包含以上六个 ZIP、说明、校验报告及 SHA256。

每个单宠 ZIP 内只有：

```text
liang-no-henshin/
  pet.json
  spritesheet.webp
```

导出目录另提供相同像素的 `spritesheet.png`。所有 cell 均为 192×208、RGBA；WebP 无损，PNG 无损。
保持全部有效帧原像素、位置、顺序与已有 alpha；仅清空未使用槽位（含历史多余的第七个 Idle cell）。
未对既有半透明工作素材做二次抠图，不改变或声称消除了这些既有像素。

## Codex

项目已验证的原生协议为 `pet.json` 中 `spriteVersionNumber: 2`、`spritesheetPath: spritesheet.webp`。
将所选 ZIP 解压得到的 `liang-no-henshin` 文件夹用于 Codex 的自定义 Pet 目录；本次只导出，不自动安装或覆盖已有宠物。
这些 ZIP 是素材归档，不声称所有 Codex 版本提供 ZIP 一键导入界面。

Gu/Feng **沿用同一个 ID `custom:liang-no-henshin`**，属于二选一的替代形态包。
不要把两个同名文件夹叠加解压；它们不会因此变成两个独立 Pet。

## DeepSeek Harness

DSH 桌宠格式取决于所用插件，不能把社区插件规范称为 Harness 唯一官方格式。
已核对 [ysyyhhh/dsh-pet 的兼容说明](https://github.com/ysyyhhh/dsh-pet/blob/master/README.zh.md)
与 [资源格式参考](https://github.com/ysyyhhh/dsh-pet/blob/master/docs/adding-a-pet.zh.md)：采用 `pet.json` + 无损 WebP/PNG，可导入 Codex 风格 ZIP。
同时核对了 [PetContract.ts](https://github.com/ysyyhhh/dsh-pet/blob/master/src/renderer/codex-pet/PetContract.ts)
和 [PetLoader.ts](https://github.com/ysyyhhh/dsh-pet/blob/master/src/renderer/codex-pet/PetLoader.ts)：
`spriteVersionNumber: 2` 对应 8×11，`1` 对应 8×9，单格 192×208。
旧资源说明只描述 9 行，因此同时提供 v2 与 legacy 包，避免擅自丢弃新方向素材。

在具有“导入 Codex ZIP”入口的兼容插件里，选择单个 `dsh-v2-*.zip`；只支持 9 行时选 `dsh-v1-legacy-*.zip`。
**不要将总包直接当成单宠 ZIP 导入。** v2 的 DSH 包与 Codex 包采用相同文件结构和像素数据。
插件是否支持 macOS 透明窗口、事件及 Look，取决于插件实现；本次未安装插件，未做 DSH 真机导入验证。

## 动作行

零起始行：0 Idle (6)、1 Right (8)、2 Left (8)、3 Waving (4)、4 Jumping (5)、
5 Failed (8)、6 Waiting (6)、7 Running (6)、8 Review (6)、9/10 Look (8+8)。
实际播放速度和事件映射由宿主控制，不能通过原生 pet.json 保证与独立 App 的逐帧时长完全相同。

## 不包含的独立 App 功能

本次为宿主原生素材包，不包含自动 Gu/Feng 时间切换、双向变身、独立 App 的 Hook 适配器或任何 runtime patch。
这些能力继续由独立 App 提供，不以额外自创字段冒充宿主支持。
本次不修改正式 App、`~/.codex`、`~/.dsh`、v0.1.1 Tag 或已发布 Release。
