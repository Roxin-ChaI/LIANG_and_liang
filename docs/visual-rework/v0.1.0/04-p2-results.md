# Five P2 items — individual disposition

2026-09-28. Isolated candidates only; no incumbent replacement, frozen-art redraw or Hook change.

| Issue | Actual disposition | Evidence and regression | Further visual approval |
| --- | --- | --- | --- |
| V-02 Feng Failed too inert | **NOT_FIXED / ASSET_REWORK_REQUIRED**. Approved adjacent frames 0→1, 3→4, 6→7 are still byte-identical. Timing cannot create absent shoulder/face action. | New [Feng window contact sheet](baseline/feng-contact-sheet.png) and [recording](baseline/feng-window-recording.gif); duplicate-pixel regression. | **MANUAL_VISUAL_QA**, approval needed for an asset revision. |
| V-03 Feng Idle breath too weak | **NOT_FIXED / MANUAL_VISUAL_QA**. Frames 0→1 and 4→5 still duplicate; most motion is eye detail. Decide whether this restraint is intentional before editing. | Same newly captured Feng sheet/recording; duplicate-pixel regression. | Manual acceptance or separately approved minimal breath artwork. |
| V-06 Effect onset/decay steps | **NOT_FIXED / ASSET_REWORK_REQUIRED**. Full 10/8 stages retained with oversized layout. The abrupt halo stages and final sparks are material content. | Newly captured [forward sequence](entry/runtime/idle-gu_to_feng-sheet.png), [reverse sequence](exit/runtime/idle-feng_to_gu-sheet.png); frame-completeness/end-dwell tests. | **MANUAL_VISUAL_QA**; no frame removal, cropping or acceleration used. |
| V-07 Renderer cadence versus 140 ms | **DIAGNOSED_NOT_FIXED / MANUAL_VISUAL_QA**. Instrumented publish→post-paint acknowledgment and acknowledgment→timer-fire using a monotonic clock. | [Ungated timing diagnostics](p2/timing-diagnostics.json). Gu→Feng renderer intervals 217–235 ms, publish→ack 71.7–85.6 ms, timer 145.3–150.9 ms; reverse intervals 231–235 ms, publish→ack 61.4–85.2 ms, timer 149.0–150.9 ms. Window visibility reported `visible`. | IPC cadence is not optical onset. Pipeline acknowledgment overhead is now measured; precise decode/RAF/compositor attribution remains **HYPOTHESIS**. No timer shortening or safety-gate removal. |
| V-08 Reverse target hard-removes overlay | **FIXED at state-machine boundary**, not an asset-continuity PASS. Finish the visible operation with its full last-frame dwell; then execute only the latest pending target. | [Actual reverse-request window sequence](p2/reverse-request-window-recording.gif), [events](p2/race-summary.json), six queue tests and live evidence regressions. | Endpoint art pops V-04/V-05 remain. Physical/optical review still **MANUAL_VISUAL_QA**. |

## Cancellation contract actually tested

- Inject 09:00 during held Gu Running. At Gu→Feng frame 4, inject 12:00. Unlike the prior hard cut, Gu→Feng displays **0–9**, commits Feng, and Feng→Gu displays **0–7** before Gu Running row 7 resumes. No NORMAL atlas report occurs between the two complete sequences.
- Latest target replaces earlier pending intent; returning to the active operation's target withdraws reversal. Duplicate requests do not restart the playhead. Task/hover updates preserve the queued target and latest underlying task.
- A reverse request now incurs a bounded delay: the remaining current sequence plus one full reverse sequence. It does not enqueue or replay every missed time node. Ordinary schedule nodes are hours apart.
- Explicit `animate=false` remains immediate and clears queued intent for accessibility/startup behavior. Historical runtime-patch/reference player behavior is untouched; the queue is an app-owned wrapper.
- Waiting→Hover→Review→hover-leave plus duplicate Feng request completed with the original operation token and resumed Feng Review. Subsequent clean forward/reverse requests ended Gu Review.

## Safety and test scope

Window captures are real Electron `capturePage`, not source PNG substitutions; the GIF is a captured-window sequence, not OS-compositor video. Test-clock and work commands are explicit QA stimuli, **not** real Desktop Hooks. The Hook definition and frozen Gu/Feng/transition files remain unchanged. Only the approved Gu registration derivative from Commit 1 is packaged via `--gu-atlas`.

P2 artistic limitations are not claimed fixed because tests pass. Final P1/P2 review remains mandatory; no Tag or release candidate is approved here.

**Final-run qualification:** the final Rework3 repeat completed the queued 10/8 reversal, but a later competing-state burst stalled at frame 4 with no renderer paint acknowledgment. Thus V-08's immediate hard-removal behavior is corrected, **not** a global cancellation/liveness PASS. The previously suspected R-01 now has a retained live failure; [final failure evidence](final/races/race-failure.json) supersedes any implication that the success trace proves the queue always settles. Its root is still HYPOTHESIS and it blocks release.
