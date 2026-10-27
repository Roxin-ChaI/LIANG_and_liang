# LIANG & liang

梁文谷 / 梁文峰双形态 macOS 像素桌宠，基于独立 Electron App。

- Gu：低能量、疲惫形态；Feng：高能量、强势形态。
- 双向变身、鼠标交互、北京时间峰谷调度。
- 可选 Codex Desktop Hook 工作状态联动；不修改 Codex 安装包。

当前版本：**v0.1.1，本机开发预览版本**。

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
