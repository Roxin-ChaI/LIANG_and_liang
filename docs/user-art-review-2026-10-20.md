# 用户视觉审核 — 2026-10-20

用户原话：「look r4 否决；四项拖拽 否决；failed 否决」。本记录覆盖这些候选此前的待审核状态，技术测试通过不能替代用户批准。

| 项目 | 本次结论 | 后续状态 |
| --- | --- | --- |
| Feng Look R4 | USER_REJECTED | 撤回眼神版候选，禁止集成或作为已批准来源 |
| Feng Look R5 | USER_REJECTED | 用户澄清：面部动作参考 Gu Look，保持 Feng 形象。撤回局部坐标形变候选，禁止集成 |
| Gu Drag Right | USER_REJECTED | 动作待返工，之前白边处理通过不构成动作批准 |
| Gu Drag Left | USER_REJECTED | 动作待返工 |
| Feng Drag Right | USER_REJECTED | 动作待返工 |
| Feng Drag Left | USER_REJECTED | 动作待返工 |
| Feng Failed 当前返工候选 | USER_REJECTED | 维持否决，不补帧、不集成 |

Failed 按当前返工上下文记录为 Feng Failed；此前已批准的 Gu Failed 不在本次候选范围。用户本条未补充新的否决原因，因此不把推测写作用户结论。

本轮只记录审核、更新候选标识。失败素材保留用于诊断，未删除原文件；未修改正式 App、atlas、素材选择配置或其它已批准动作。

Feng Look R4 的具体标识在 `assets/rework/v0.1.0/feng-look-r4-2026-10-06/review-status.json`。四项拖拽及 Feng Failed 的结论在 R2 目录的 `review-status.json` 补充记录。后续制作必须另立候选，保留原有动作要求和人工审核流程。
