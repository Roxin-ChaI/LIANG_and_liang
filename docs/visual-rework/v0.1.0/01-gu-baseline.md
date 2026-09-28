# V-01 baseline correction — candidate PASS

The canonical is unchanged formal Gu Idle, foot y=203. `tools/rework_gu_baseline.py` derives `assets/rework/v0.1.0/gu/spritesheet.webp` by translating the 30 effective Waving/Failed/Waiting/Running/Review cells down exactly5 px. No resampling, scaling, recoloring, mirroring, frame replacement or temporal reordering occurs. Every source RGBA byte is retained in the translated cells, unchanged cells are byte-identical, no visible pixel is cropped, and the lossless WebP roundtrip is exact. The formal/frozen atlas is retained untouched.

- Before: those five work rows foot y=198; Idle y=203.
- After: all five rows foot y=203; Idle unchanged y=203.
- Candidate SHA256: `b5b6b6b4fd437164282c5ba4c3b1de8f4b74e0184148eba344118e5e0fa97968`.
- Skill v2 validator: PASS, 1536×2288 RGBA, no hidden RGB residue, no errors/warnings. No additional despill was performed because none was necessary.

[Source before/after](../../../assets/rework/v0.1.0/gu/baseline-before-after.png), [actual-window Gu Contact Sheet](baseline/gu-contact-sheet.png), [window recording](baseline/gu-window-recording.gif), [81 state-pair captures](baseline/gu-state-pairs.png), [window metrics](baseline/window-metrics.json).

The separate Rework1 App was built with an explicit `--gu-atlas` override that only changes the candidate's packaged Gu atlas input. Its isolated window captured all expected standard frames and16 looks in both forms. Gu's 81 ordered state pairs and four finite-row→Idle handoffs completed, with no blank or edge-touching sprite. All work/Idle window baselines were227.5 CSS px (the half-pixel value results from reporting the bottom physical pixel at device scale2), with zero baseline difference.

The original work poses remain ~194 px tall versus ~200 px Idle because translation cannot and must not change their proportions. This commit fixes **only the confirmed foot-position defect**, not any remaining pose/identity judgment, transition endpoint problem or P2. It does not establish VISUAL_QA_PASS. No current App bundle was overwritten or relaunched; only a new `dist/Liang no Henshin v0.1.0 Rework1.app` was used with temporary userData.

Relevant tests:6 PASS (pixel-preservation/clipping/build override/window baseline and existing builder tests); live baseline predicate PASS; v2 validator PASS. Original-audit xfail remains against the historical frozen source; a new candidate assertion is required to pass.
