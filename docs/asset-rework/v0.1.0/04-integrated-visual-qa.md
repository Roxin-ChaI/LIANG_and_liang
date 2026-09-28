# Integrated asset rework QA — VISUAL_QA_FAIL

The no-redraw asset gate failed safely: **NEEDS_MANUAL_ART_REDESIGN**. No replacement
transition animation was generated. This report tests the **fixed player with
unchanged art**, not a newly reworked asset sequence. New-art integration is
**NOT_TESTED / BLOCKED_ART**. No Tag, release candidate or incumbent replacement.

## Endpoint comparison and actual modification scope

The new [endpoint specification](01-transition-endpoint-spec.md) locks Gu/Feng
canonical Idle plus phase-matched Running, logical x=96 and ground y=203. Old art
has alternate Gu head/face/torso drawings; rigid alignment cannot supply missing
intermediate poses. Idle's differences are relatively small; Running's before→0
head lift and reverse7→normal head drop remain plainly visible at a grounded foot.

Actual transition-art changes: **zero**. [Reuse diagnostics](02-transition-reuse-decision.md)
show why endpoint-only copying relocates rather than repairs the discontinuity.
Required future art scope is reviewed Gu entrance0–2 and convergence5–7, matched
to Idle and actual Running phases, plus authored character/effect masks.

Old/new-player comparisons (the art is explicitly unchanged):

- [Idle forward](integrated/transitions/idle-gu_to_feng-prior-vs-fixed-player.png),
  [Running forward](integrated/transitions/running-gu_to_feng-prior-vs-fixed-player.png).
- [Idle reverse](integrated/transitions/idle-feng_to_gu-prior-vs-fixed-player.png),
  [Running reverse](integrated/transitions/running-feng_to_gu-prior-vs-fixed-player.png).

[Independent review](integrated/independent-visual-review.json) rates the current
Running discontinuities nearer **P2**, not P1; its Idle/Hover observations are
warnings. This qualification is preserved, not overridden. Historical V-04/V-05
remain unresolved endpoint gates, without an automatic severity downgrade or
release approval. Intended broadening/shrinking and different intermediate hull
sizes are not themselves failures.

## Frame4 and operation recovery

[Investigation](03-frame-ack-stall.md) separates the reproduced negative-age /
RAF-chain failure from the **unproven exact historical exception**. The repair
also guards decode/readiness generations and acknowledges successful delivery,
not queued callbacks. Main's operation-token validation and full 140 ms post-paint
dwell remain unchanged; no skips, hidden frames, faster playback or fabricated ack.

The isolated **AckFix** build actually launched with its own temporary HOME and
userData; Hooks were disabled only for the test process. Tests did not use Codex
installation files or Hook events as synthetic Desktop evidence.

- Six actual frame-gated scenes: Idle/Running/Hover × both directions. All10/8
  stages are retained, last-stage→completion143–151 ms. Idle resumes row0,
  Running resumes row7, Hover resumes row4.
- Two ungated timing scenes plus two separately launched race sessions. Reverse
  requests at frame4 defer through the full original sequence; duplicate targets
  don't restart; Waiting/Hover/Review bursts restore latest Review; consecutive
  peak/off-peak requests complete and settle to Gu. Every op token completes once.
- Four additional **ungated** actual-window GIF recordings cover Idle/Running
  both directions with observed capture intervals, not uniform fake140 ms pacing.
- Total: **24 operations /216 ordered transition-frame acknowledgments**;
  **zero frame4 stalls observed** in fixed runs. Every stage has paint→dwell→end
  before the next stage. Finite runs are not a proof of universal stall freedom.

Machine checks: [six scenes/timing](integrated/transitions-ack.json),
[race1](integrated/race-1-ack.json), [race2](integrated/race-2-ack.json),
[ungated recordings](integrated/ungated-ack.json).
[Prior stuck frame vs completed Review](integrated/frame4-prior-vs-fixed-player.png).

## Visual artifacts and timing limits

- Complete full-window sheets (oversized effects **not** cropped to normal cell):
  [Idle forward](integrated/transitions/idle-gu_to_feng-full-window-sheet.png),
  [Idle reverse](integrated/transitions/idle-feng_to_gu-full-window-sheet.png),
  [Running forward](integrated/transitions/running-gu_to_feng-full-window-sheet.png),
  [Running reverse](integrated/transitions/running-feng_to_gu-full-window-sheet.png).
- All54 individual intermediate window PNGs: `integrated/transitions/frames/`.
  Hover sheets/GIFs are retained alongside Idle/Running.
- [Ungated Idle forward GIF](integrated/ungated/idle-gu_to_feng-ungated-window.gif),
  [Idle reverse GIF](integrated/ungated/idle-feng_to_gu-ungated-window.gif),
  [Running forward GIF](integrated/ungated/running-gu_to_feng-ungated-window.gif),
  [Running reverse GIF](integrated/ungated/running-feng_to_gu-ungated-window.gif).
- [Frame capture timeline](integrated/transitions/transition-timeline.json),
  [ungated timestamps](integrated/ungated/ungated-timeline.json),
  [race1](integrated/race-1/race-summary.json), [race2](integrated/race-2/race-summary.json).

`webContents.capturePage` records the real composed Electron window, not OS desktop
occlusion. Frame-gated GIFs reconstruct selected frames and prolong capture time.
Ungated sampling does not hold the playhead, but capture adds load and may miss a
display frame; acknowledgments independently confirm all stages. GIF quantizes
color/timing; preserved PNGs remain the pixel reference. In the first ungated
timing pass actual paint-to-paint intervals217–235 ms included decode/paint overhead
in addition to140 ms main dwell. We did not speed up frames to conceal art defects.

## Regression, integrity and disposition

Full regression: **Python303 PASS, 1 historical expected failure, 12 subtests PASS;
Node216 PASS**, zero unexpected failures. The historical xfail preserves the
unmodified formal Gu work-row defect; the already-corrected candidate passes its
separate tests. Diff checks run before this commit. New regression
coverage rejects missing frame4 acknowledgments, bad order, duplicate completion,
short dwell and renderer errors; a timer PASS explicitly **does not imply art PASS**.

The [review ledger](integrated/review.json) records hashes and limits. Formal Gu/Feng
atlases, existing corrected Gu candidate, all18 frozen overlays and authorized Hook
definitions remain unchanged against24b0df1. Official Codex was not modified.
Only our test instances exited; temporary profiles cleaned, no test process left.
Ignored `dist` candidate builds and ignored raw QA traces are retained for diagnosis;
no installation or background service was created.

**VISUAL_QA_FAIL.** Next prerequisite is an explicitly reviewed manual transition
art-redesign workflow; after real intermediate drawings exist, repeat the same
Idle/Running boundary checks with natural playback. Renderer recovery progress
does not waive the remaining endpoint requirements.
