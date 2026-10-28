# LIANG & liang

梁文谷 / 梁文峰双形态 macOS 像素桌宠，基于独立 Electron App。

- Gu：低能量、疲惫形态；Feng：高能量、强势形态。
- 双向变身、鼠标交互、北京时间峰谷调度。
- 可选 Codex Desktop Hook 工作状态联动；不修改 Codex 安装包。
- 同一套 Gu / Feng 素材也提供 **Codex Pet** 与 **DeepSeek Harness（DSH）兼容桌宠插件**使用的素材包。

当前版本：**v0.1.1，本机开发预览版本**。

## Codex / DSH 桌宠素材下载

除了独立 macOS App，本项目还将 v0.1.1 素材制作成 `pet.json` + 无损 WebP 图集的桌宠包，无需运行本项目的独立 App 即可交给兼容宿主加载。

| 格式 | 梁文谷 Gu | 梁文峰 Feng | 规格 |
|---|---|---|---|
| Codex Pet v2 | [下载 Gu](https://github.com/Roxin-ChaI/LIANG_and_liang/releases/download/v0.1.1/LIANG_and_liang-v0.1.1-codex-v2-gu.zip) | [下载 Feng](https://github.com/Roxin-ChaI/LIANG_and_liang/releases/download/v0.1.1/LIANG_and_liang-v0.1.1-codex-v2-feng.zip) | 1536×2288，8×11，含 16 个 Look 方向 |
| DSH v2 兼容包 | [下载 Gu](https://github.com/Roxin-ChaI/LIANG_and_liang/releases/download/v0.1.1/LIANG_and_liang-v0.1.1-dsh-v2-gu.zip) | [下载 Feng](https://github.com/Roxin-ChaI/LIANG_and_liang/releases/download/v0.1.1/LIANG_and_liang-v0.1.1-dsh-v2-feng.zip) | 同上，适用于支持 Codex v2 的 DSH 桌宠插件 |
| DSH 旧版兼容包 | [下载 Gu](https://github.com/Roxin-ChaI/LIANG_and_liang/releases/download/v0.1.1/LIANG_and_liang-v0.1.1-dsh-v1-legacy-gu.zip) | [下载 Feng](https://github.com/Roxin-ChaI/LIANG_and_liang/releases/download/v0.1.1/LIANG_and_liang-v0.1.1-dsh-v1-legacy-feng.zip) | 1536×1872，8×9，不含 Look |

[全部素材总包](https://github.com/Roxin-ChaI/LIANG_and_liang/releases/download/v0.1.1/LIANG_and_liang-v0.1.1-pet-formats.zip) · [素材包 SHA256](https://github.com/Roxin-ChaI/LIANG_and_liang/releases/download/v0.1.1/PET_SHA256SUMS.txt) · [格式及使用说明](docs/pet-format-exports.md)

每个单宠 ZIP 内含 `liang-no-henshin/pet.json` 与 `spritesheet.webp`。总包需先解压，再选单宠 ZIP 导入；不要把总包当作一只宠物导入。
Gu/Feng 沿用同一个 Pet ID，属于二选一的形态包。原生素材包不包含独立 App 的时间调度及双向变身，播放行为由宿主决定。
DSH 兼容性依据支持 Codex 格式的社区插件规范；已通过格式与像素校验，尚未做 DSH 真机导入验收。

## 文档

- [v0.1.1 发布说明与已知限制](docs/releases/v0.1.1.md)
- [v0.1.0 历史发布说明](docs/releases/v0.1.0.md)
- [独立 App 构建与运行](standalone-app/README.md)
- [最新已批准素材接入及验收](docs/approved-actions-integration-2026-10-23.md)

注意：手动切换形态暂不锁定，自动调度会重新校正。v0.1.1 已接入获批的 Gu/Feng Look 修复。
当前构建包含本机路径假设，尚非通用安装器；不要自动信任仓库 Hook，启用前应检查路径与权限。

## 目录

- `standalone-app/`：当前桌宠应用。
- `assets/`：标准图集、变身及带审核记录的派生素材。
- `tools/`、`tests/`：构建、校验和回归测试。
- `docs/`：阶段记录、素材审批与已知问题。
- `runtime-patch/`：历史研究、项目拥有的动画组件及测试工具。旧 Codex patch/signing 实验已停止，不是当前 App 的安装步骤。

本仓库保留开发历史和失败素材供追溯，不应把任意历史候选当作已批准资源；当前选择以 `standalone-app/asset-overrides.json` 为准。
