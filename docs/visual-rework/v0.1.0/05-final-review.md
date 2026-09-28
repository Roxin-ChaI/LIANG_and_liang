# v0.1.0 Visual Rework — VISUAL_QA_FAIL

Date: 2026-09-28, Asia/Shanghai. **No Tag, no release candidate, no incumbent replacement.** This is a partial rework with retained failures, not an all-P1-cleared sign-off.

## Three original P1 items: before / after

| Issue | Before | After and verdict |
| --- | --- | --- |
| V-01 Gu five work-row feet | Waving/Failed/Waiting/Running/Review y=198; canonical Idle y=203. | **FIXED_REGISTRATION_ONLY**: exactly30 effective cells translated down5 px, now y=203. Every translated RGBA pixel preserved, other cells unchanged, no interpolation/scale/reorder/crop. Actual Idle↔work shoes match at 1×/2×. Original work poses remain more compact than Idle; no anatomical redesign was attempted. |
| V-04 Gu→Feng entry | Alternate Gu endpoint face/torso and lateral registration pop. | **ASSET_REWORK_REQUIRED / P1 remains**. Idle rigid candidate dx=-8 aligns rough proxies but not face/pose. Running best dx=-3 still leaves4.5 px head-proxy residual; vertical matching would disturb grounded feet. No partial offset, hidden frame or acceleration applied. Actual Idle/Running/Hover before→0 remains visibly discontinuous. |
| V-05 Feng→Gu exit | Final Gu endpoint changes pose/position on normal-row takeover. | **ASSET_REWORK_REQUIRED / P1 remains**. Idle dx=-8 and Running dx=-2 roughly align proxy bands but not the head/face/torso drawing. All8 stages retained. Gu Running recovery row7 and its foot baseline now PASS, but endpoint pose continuity does not. |

[Old actual Idle/Running comparison](../../visual-audit/v0.1.0/gu-idle-vs-running-baseline.png) → [new comparison](final/gu-idle-vs-running-baseline.png). [Integer-only source before/after](../../../assets/rework/v0.1.0/gu/baseline-before-after.png). [Entry rigid feasibility](entry/gu_to_feng-feasibility.json), [exit rigid feasibility](exit/feng_to_gu-feasibility.json). Overall alpha hull and dark proxies are not anatomical head segmentation; intentional leaning, gestures, hopping and transformation growth are not failed for changing bbox alone.

## Actual final candidate and complete coverage

Candidate: `dist/Liang no Henshin v0.1.0 Rework3.app`, project-owned ad-hoc build,40 resource files. The explicit `--gu-atlas assets/rework/v0.1.0/gu/spritesheet.webp` override packages the corrected derivative; the default/formal build input is deliberately not replaced.

- Gu candidate SHA256: `b5b6b6b4fd437164282c5ba4c3b1de8f4b74e0184148eba344118e5e0fa97968`. Packaged Gu matches exactly.
- Feng SHA256 remains `d697e573268b66cb0f6a062480ec87c8c11712ca34b57f8c2fc0a97ed6e2164a`. Packaged Feng matches exactly.
- Candidate v2 validator PASS: RGBA1536×2288, no hidden RGB residue, no errors/warnings. No despill/resampling performed.
- All9 standard rows, all57 expected row frames per form, and16 directions per form captured at forced1× and2×: **no missing frame**. Gu125/Feng125 captures at1×; Gu119/Feng117 at2×. [Coverage/geometry ledger](final/window-metrics.json).
- 162 ordered state pairs,81 per form: correct requested row reached, nonempty post-paint window, zero window-edge contact. Four finite-row→Idle handoffs per form reached Idle. This establishes settled boundary routing, not absence of every sub-frame compositor flash.
- Six actual transition scenarios: Idle/Running/Hover × both directions. Every forward0–9 and reverse0–7 captured; last frame dwell retained. Held Running resumes row7 after both directions. See [timeline](final/transitions/transition-timeline.json).

## New contact sheets, sequences and handoffs

- [Gu2× contact](final/gu-contact-sheet.png), [Feng2× contact](final/feng-contact-sheet.png), [Gu1× contact](final/gu-1x-contact-sheet.png), [Feng1× contact](final/feng-1x-contact-sheet.png).
- [Gu captured-window sequence](final/gu-window-recording.gif), [Feng sequence](final/feng-window-recording.gif).
- [Gu16 directions](final/gu-look-directions.png), [Feng16 directions](final/feng-look-directions.png).
- [Gu81 pair matrix](final/gu-state-pairs.png), [Feng81 pair matrix](final/feng-state-pairs.png).
- Gu→Feng: [Idle](final/transitions/idle-gu_to_feng-sheet.png), [Running](final/transitions/running-gu_to_feng-sheet.png), [Hover](final/transitions/hover-gu_to_feng-sheet.png).
- Feng→Gu: [Idle](final/transitions/idle-feng_to_gu-sheet.png), [Running](final/transitions/running-feng_to_gu-sheet.png), [Hover](final/transitions/hover-feng_to_gu-sheet.png). Each corresponding `*-window-recording.gif`, before/first/last/after PNG and time ledger is retained in the same directory.

These are real isolated Electron `webContents.capturePage` frames. GIFs are composed from captured windows; **not OS-compositor recordings or optical timing measurements**. No source-frame substitution is used. External Retina/fractional display behavior, physical pointer interaction and this candidate's real-Hook concurrency remain **MANUAL_VISUAL_QA / NOT_VERIFIED**. Test state/clock commands are not portrayed as genuine Desktop Hook events.

## P2 disposition and additional final findings

See the [five-item P2 ledger](04-p2-results.md). V-02 Failed, V-03 Idle breath and V-06 effect staging remain asset/manual issues. V-07 has measured monotonic publish→paint-ack and dwell diagnostics but is **DIAGNOSED_NOT_FIXED**:140 ms is post-ack dwell, not total renderer interval; cadence remains217–235 ms. No frame-speed workaround was introduced.

V-08 hard-removal policy was repaired: complete current transition, then run latest pending target; no intermediate NORMAL atlas flash in the observed two-operation reversal. Latest task state is retained and duplicate targets do not restart. **This is not a global liveness PASS**:

- **R-01 / P1 runtime blocker, observed**: the final run first completed queued Gu→Feng10/Feng→Gu8 and resumed Gu Running. A subsequent duplicate target plus Waiting→Hover→Review→hover-leave burst at frame3 published frame4 but never produced its renderer report/paint acknowledgment. The next reverse target remained pending and the test timed out. The actual stalled screenshot and sanitized token/timer trace are [retained here](final/races/race-failure.json), [window](final/races/stalled-after-competing-states.png).
- First missing **observed** stage: renderer post-paint report for frame4. No timer for that frame starts because the player correctly waits for acknowledgment. **Root remains HYPOTHESIS**: asynchronous renderer/report/RAF scheduling; these traces do not prove an exact code fault or OS cause. The prior early intermittent risk is now reproduced on the latest candidate. No retry-success was substituted for this failure.
- **LOOK-FENG-000 / independent P1 review concern**: labeled reviewer cannot certify Feng000 as unmistakably Up;337.5→000 is a continuity warning. [Independent visual review](final/independent-visual-review.json) records all32 labeled direction judgments. This is **not** blind direction certification or proof of a wrong quadrant; manual/blind reapproval is needed before any authorized direction-art change. Frozen looks were not edited.

## Regression and safety

- Python: **289 passed,1 xfailed,12 subtests passed**. The sole xfail is against the intentionally unchanged historical formal Gu y198 baseline; corrected candidate assertions PASS. Coverage/evidence regressions preserve the live failure instead of promoting it to PASS.
- Node: **208 passed**. Historical runtime-patch tests are project-code regressions only; no ASAR patching, signing of Codex, runtime injection or real Codex launch was performed.
- Every stage ran relevant tests and `git diff --check`; commits are independent, no amend.
- Formal `assets/builds`, Gu/Feng source assets, transition assets and authorized `.codex` definitions unchanged relative to `7f865ae`. No official Codex App or user configuration was targeted by a write.
- Original standalone PID51098 and receiver PID51105 retain their original start times. They were not exited, replaced or relaunched. Every rework test used temporary home/userData with real-Hook forwarding disabled; test quit/temporary-directory cleanup also ran on the failed test. No Rework/audit test process remained at final process check. Ignored candidate build bundles and raw QA traces are intentionally retained locally.

Commits before this final report: `0ae66d1` (baseline), `f5089b7` (entry blocker), `fd5ed86` (exit/recovery blocker), `8f0876d` (P2 queue/timing). This final review is submitted independently; no Tag is created.

## Next repair order

1. Diagnose R-01 with a deterministic renderer-ack race repro and narrowly fix the actual renderer failure; verify full-frame completion under repeated state bursts before claiming scheduler/queue liveness.
2. Obtain explicit approval for state-matched Gu transition entrance/exit artwork or an approved canonical handoff contract. Integer registration alone cannot reconcile different face/torso poses across Idle and Running; do not warp, hide or rush existing frames.
3. Resolve Feng Up cardinal/adjacent continuity with independent blind/manual review. Then separately approve Failed/breath/effect revisions, and repeat timing, physical pointer, display and real-Hook visual QA.

**VISUAL_QA_FAIL — release candidate BLOCKED.** V-01 foot registration is repaired; V-04/V-05 remain, and the retained live stall must not be hidden behind passing unit tests.
