# v0.1.0 comprehensive visual audit — VISUAL_QA_FAIL

Audit date: 2026-09-28, Asia/Shanghai. This report supersedes the **visual** acceptance implied by the earlier QA2 candidate report; its automated functional results remain useful. No v0.1.0 tag is authorized by these results.

## Evidence and limits

- Actual, isolated, packaged QA2 Electron windows: both forms, nine standard rows each, every expected frame, 16 look directions per form, forced 1×/2× device scales.
- [Gu contact sheet](gu-contact-sheet.png), [Feng contact sheet](feng-contact-sheet.png), [Gu actual-window capture sequence](gu-window-recording.gif), [Feng capture sequence](feng-window-recording.gif), [16 Gu looks](gu-look-directions.png), [16 Feng looks](feng-look-directions.png).
- [Six transition scenario sheets/recordings](02-transition-audit.md), [per-frame transition times](transitions/transition-timeline.json).
- Every ordered 9×9 row pair per form (162 total) reached the requested row, with nonempty post-paint captures and no window-edge alpha contact: [Gu pair matrix](findings/gu-state-pairs.png), [Feng pair matrix](findings/feng-state-pairs.png), [coverage ledger](findings/state-pair-coverage.json). Four finite-row-to-Idle handoffs per form were observed. This proves settled boundary routing, **not** every possible sub-frame flash.
- [Source attribution](findings/source-attribution.json), [runtime race outcomes](races/race-summary.json). Raw screenshot sequences/traces remain locally in ignored `standalone-app/evidence/v010-*` directories.

The recorded PNGs are real `webContents.capturePage()` output of the running QA2 window, not source-frame substitutions. GIFs are composed from those captures. They are **not** an OS-screen/compositor video; optical timing, external Retina monitor behavior, fractional display scaling, user-resized windows and physical pointer gestures are **NOT_VERIFIED**. The App has a fixed normal 192×208 pet region within a 256×256 transparent window; it was not rewritten to allow resizing. Live Codex Hooks were disabled only in the isolated test process, so real-Hook concurrency is **NOT_VERIFIED** this run and prior Phase 2 evidence is not substituted for it.

Overall alpha bounds are not anatomical body/head measurements. Lifted hands, leaning drag poses, the intentional 3–4 px hover rise and transformation growth were not failed merely for changing silhouette. In particular, transition full-alpha widths include blue energy; they cannot prove head scaling. Dark body proxies below exclude cyan effects but still include pose extrema, not a head segmentation.

## Observed rework backlog, sorted by severity

No P0 defect has been established in this run.

### V-01 — P1: Gu grounded-state foot/height jump

- Form/animation/frames: Gu Idle/Drag versus all Waving, Failed, Waiting, Running and Review frames; most obvious Running→Idle and finite-row completion.
- Evidence: [Idle versus Running](gu-idle-vs-running-baseline.png), Gu recording/contact sheet, source ledger.
- Repro: start Gu; enter Running; Stop/return Idle. Repeat with each of the five named rows. The feet jump 5 CSS px down on return; character height also changes. Source atlas bottom is y=203 for Idle/Drag and y=198 for those work rows. Window captures reproduce exactly that delta.
- Root: **CONFIRMED — material/coordinate registration inside the frozen atlas**, not device-scale resampling. No rendering fix can make the existing source positions consistent without changing placement.
- Suggested repair: re-register the five rows against approved Idle, using foot/torso anchors and identity checks; inspect actual head/body proportions rather than translating blindly. This requires explicit approval to change the frozen baseline/material, not a silent runtime offset.
- Regression: source baseline predicate now documents an expected failure; final-size boundary screenshot comparisons can cover it. Human visual reapproval: **YES**.

### V-04 — P1: Gu→Feng entry pose/registration pop

- Form/animation/frames: Gu normal state→Gu→Feng frame 0, all three entry modes.
- Evidence: [Idle before](transitions/idle-gu_to_feng-before.png) → [frame 0](transitions/idle-gu_to_feng-00.png), [Running sheet](transitions/running-gu_to_feng-sheet.png), [Hover sheet](transitions/hover-gu_to_feng-sheet.png).
- Repro: switch Gu→Feng from Idle, Running or Hover. The head/torso drawing changes immediately before the staged effect growth. The official Idle full-body hull center is x=88; the effect-excluded endpoint proxy is x=96. Both are ~200 px tall. The 8 px center-proxy difference identifies a registration/pose discontinuity, not proof that the entire person has been scaled 29%.
- Root: **CONFIRMED source/registration mismatch at the handoff**; exact anatomical head-size attribution is **HYPOTHESIS**. The effect overlay uses its x=96 anchor while Gu's approved idle has an asymmetric/leaning silhouette. A single translated bbox does not automatically fix facial pose or shoes.
- Suggested repair: approved pose-matched endpoints and a reviewed handoff contract for Idle/Running/Hover; retain all 10 stages and dwell. Do not hide frame 0 or accelerate playback.
- Regression: endpoint/body registration checks and actual before→first screenshot comparisons; image identity requires human judgment. Human reapproval: **YES**.

### V-05 — P1: Feng→Gu exit pose/registration pop

- Form/animation/frames: Feng→Gu frame 7→target Gu normal state.
- Evidence: [frame 7](transitions/idle-feng_to_gu-07.png) → [Gu after](transitions/idle-feng_to_gu-after.png); all entry-mode sheets.
- Repro: switch Feng→Gu; inspect the final transform frame and first target-row frame. The drawn Gu pose/face and horizontal placement change abruptly. Final dark proxy is x=96.5, height199; approved Gu Idle hull is x=88, height200. There is no evidence of a large endpoint height-scale error, but the registration/pose pop is visible.
- Root: **CONFIRMED source/registration endpoint mismatch**; anatomical head-size distortion remains **HYPOTHESIS**.
- Suggested repair: pose-match the final transform image to an approved Gu handoff, without silently redrawing frozen art or masking frame 7. Combine with V-01 so a work-state recovery does not introduce a second baseline pop.
- Regression: final→target screenshot/anchor checks, plus all 8 displayed frames retained. Human reapproval: **YES**.

### V-02 — P2: Feng Failed under-communicates failure

- Form/animation/frames: Feng Failed 0→1, 3→4, 6→7 are exact adjacent duplicates; remaining changes are tiny eye changes.
- Evidence: [Failed frame 0 versus 4](feng-failed-frame-0-vs-4.png), Feng recording, source duplicate list.
- Repro: trigger Failed and observe all 8 frames. Structurally valid playback looks almost like Idle; no persuasive setback/recovery is apparent.
- Root: **CONFIRMED material-content limitation**, not missing renderer frames. Visual adequacy is an artistic judgment.
- Suggested repair: obtain approval for more legible restrained eyebrow/shoulder action while keeping identity/proportions. Do not invent new emotion or change body type.
- Regression: duplicate/difference-area metrics catch inert frames but cannot approve emotion. Human reapproval: **YES**.

### V-03 — P2: Feng Idle breath cycle is visually very weak

- Form/animation/frames: Feng Idle 0→1 and 4→5 duplicate exactly; all other changes are in the eye region.
- Evidence: Feng contact sheet/recording; source and window RGB difference ledgers.
- Repro: leave Feng idle for several loops. There is eye activity but no visible chest/shoulder breathing in the captured window.
- Root: **CONFIRMED material content**. Whether this is too restrained is subject to human approval, not a runtime malfunction.
- Suggested repair: approve either the static stance as intentional or a minimal chest/shoulder breath. No forced equal-bbox or exaggerated-motion rule.
- Regression: changed-area/duplicate metrics only; human reapproval: **YES** if altered.

### V-06 — P2: effect onset/exit steps need artistic review

- Form/animation/frames: Gu→Feng 1→2→3 and late effect decay; Feng→Gu trailing sparks at frame 7→normal.
- Evidence: both Idle transition sheets and recordings.
- Repro: watch the blue halo expand in ~two stages and disappear on normal-row takeover. No cropped halo was seen at the tested viewport, but abrupt energy changes alter visual balance.
- Root: **CONFIRMED material/effect staging**, acceptability undecided. Overall energy bbox growth is *not* character scale evidence.
- Suggested repair: approve or refine energy continuity in a separately authorized asset revision; do not drop frames, crop the aura or accelerate to conceal it.
- Regression: effect occupancy/delta metrics can flag large steps; human reapproval: **YES**.

### V-07 — P2: timing discrepancy requires instrumentation

- Form/animation/frames: both complete transitions, ungated QA2 renderer events.
- Evidence: ungated timestamps in [timeline](transitions/transition-timeline.json): Gu→Feng217–234 ms, Feng→Gu233–234 ms between reported frames; configured timer140 ms. Last reported frame→completion153/155 ms.
- Repro: run `audit_standalone_transitions.py`; inspect `ungatedTimings`, not the screenshot-gated pass. The frame gate intentionally adds capture delay and must not be used to judge normal speed.
- Root: **HYPOTHESIS — renderer scheduling/paint acknowledgment/display throttling**. The main timer begins after render acknowledgment, so decode/paint delay adds to the configured dwell. Optical on-screen onset is not measured here.
- Suggested repair: instrument monotonic paint/timer deadlines and foreground/occlusion state before changing timing. Do not shorten frame dwell to conceal V-04/V-05.
- Regression: time-injected player tests plus live timing bounds in a controlled display environment. Human visual timing approval: **YES**.

### V-08 — P2: reverse time target hard-cancels visible transformation

- Form/animation/frames: Running, Gu→Feng frame 4→Gu Running.
- Evidence: [before reverse target](races/running-gu-to-feng-before-cancel.png) → [after](races/gu-running-after-cancel.png), race ledger.
- Repro: start08:59 Gu/Running; inject09:00; at transform frame4 inject12:00. The correct off-peak target wins immediately, but the oversized energy/body image is abruptly removed. This corresponds to a clock jump or rapid manual reversal, not ordinary schedule nodes hours apart.
- Root: **CONFIRMED state-machine cancellation policy**: reverse target to the still-committed form cancels the operation and the renderer removes the overlay. No stale completion or historical backfill was seen.
- Suggested repair: choose and approve a visual cancellation contract (settle/reverse safely, preserving latest target and task). Do not delay the schedule indefinitely or replay historical transitions.
- Regression: existing token/cancel tests cover final state; the added live repro covers the visible boundary. Human visual reapproval: **YES**.

## Simultaneous events and potential risks (not confirmed defects)

- In retained live race runs, a duplicate Feng target plus rapid Waiting→Hover→Review→hover-leave updates preserved the operation token and completed in Feng Review. Clean consecutive Gu→Feng→Gu completed, ending in Gu Review without observed frame residuals. Reverse-time cancellation ended Gu Running and did not replay missed nodes.
- **R-01, HYPOTHESIS:** two early experimental race runs timed out after a burst at transform frame3 with the event tail at frame4; later two retained end-to-end replays completed. One subsequent audit-harness attempt also incorrectly began the next clock step before awaiting recovery and was corrected. There is insufficient retained visual evidence to classify an intermittent paint-ack stall as a confirmed defect. Add per-renderSerial/decode/ack/deadline instrumentation and a repetition stress test; do not claim the success runs prove absence of a race.
- **R-02, NOT_VERIFIED:** physical drag/hover conflicts, actual external Retina/fractional scale and OS-compositor flashes. Ordered-state screenshots and forced scale cannot certify these.
- **R-03, NOT_VERIFIED:** a live Desktop Hook burst against the isolated QA2 build. Test commands exercised the actual App's state interface but were not presented as genuine Hook events.
- **R-04, HYPOTHESIS:** look direction semantic jumps around Feng67.5→90.0 may require human approval. All16 frames and order are confirmed; exact gaze interpretation cannot be proved from row indices.

## Recommended repair order

1. Decide the canonical Gu registration and fix V-01 with approved atlas QA; freeze the new baseline only after final-size identity review.
2. Approve pose-matched entry/exit endpoints, fixing V-04/V-05 together. Verify Idle, held Running and Hover handoffs at full sequence length.
3. Diagnose R-01/V-07 with paint/timeline instrumentation before engine changes; keep latest-state/token guarantees.
4. Decide cancellation behavior V-08; review effect continuity V-06 without hiding material frames.
5. Review Feng Failed/Idle action strength V-02/V-03, then repeat physical/Retina/real-Hook visual QA.

## Regression, integrity and verdict

- Python full regression: **274 passed, 1 xfailed, 12 subtests passed**. The xfail is the desired consistent Gu-baseline assertion exposing V-01; it is not a visual PASS.
- Node full regression: **202 passed**.
- Protected paths unchanged relative to audit starting HEAD `44d518f`: formal/frozen `assets/`, authorized `.codex/`, and standalone business main/renderer/scheduler. Only audit tools, tests, documents and curated QA evidence were added/updated.
- Every test launch used its own temporary home/userData with Codex-event integration disabled and exited via the App's test quit control. Temporary directories were removed. The incumbent standalone process PID51098 and receiver PID51105 use ordinary userData and were left untouched; they were not treated as audit processes to terminate.
- No official Codex App, user configuration, frozen sprite pixel, Hook definition, installer/startup setting or tag was changed by this audit. No replacement of the running incumbent App occurred.

**VISUAL_QA_FAIL**: automated frame coverage/functional tests pass, but confirmed visible baseline and endpoint-registration/pose discontinuities remain. This report proposes rework; it does not perform it.
