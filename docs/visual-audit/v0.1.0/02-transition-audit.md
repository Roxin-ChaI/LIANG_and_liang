# QA2 bidirectional transition visual audit

Six isolated QA2 window scenarios were captured: Gu→Feng (10 displayed frames) and Feng→Gu (8 displayed frames), each entered from Idle, Running and Hover. The frame-capture gate makes each transformed frame screenshotable and preserves renderer paint order. Per-frame times from that gated pass are **not** ordinary playback times. A second, ungated pass measured renderer event intervals. The tests use `webContents.capturePage()` of the real QA2 Electron window, not source artwork. They do not prove final macOS compositor timing or physical mouse interaction.

Evidence: [timestamp and geometry ledger](transitions/transition-timeline.json). Every sheet shows before, each numbered transformation frame, and after:

| Entry | Gu→Feng | Feng→Gu |
| --- | --- | --- |
| Idle | [10-frame sheet](transitions/idle-gu_to_feng-sheet.png) · [window recording](transitions/idle-gu_to_feng-window-recording.gif) | [8-frame sheet](transitions/idle-feng_to_gu-sheet.png) · [window recording](transitions/idle-feng_to_gu-window-recording.gif) |
| Running | [10-frame sheet](transitions/running-gu_to_feng-sheet.png) | [8-frame sheet](transitions/running-feng_to_gu-sheet.png) |
| Hover | [10-frame sheet](transitions/hover-gu_to_feng-sheet.png) | [8-frame sheet](transitions/hover-feng_to_gu-sheet.png) |

## Actual observations

- **V-04, P1 — Gu→Feng starts with a proportion jump.** Repro: start in Gu Idle, trigger Feng. The Gu immediately changes between the normal window frame and transition frame 0: the alpha width at requested 2× scale grows from 136 to 176 pixels and the facial/shoulder drawing changes. The boundary differs at 45,988 displayed pixels in the Idle capture. See [before](transitions/idle-gu_to_feng-before.png) and [frame 0](transitions/idle-gu_to_feng-00.png). Running/Hover entries show the same transform-frame-0 art; their differences are also large. A legitimate staged enlargement later in the transformation is not itself called a defect here.
- **V-05, P1 — Feng→Gu ends with a proportion jump.** Repro: start in Feng Idle, trigger Gu, watch frame 7 to the returning Gu idle. The final transition frame still shows a larger/different Gu head and shoulder/body shape than the immediately following official idle. In the Idle window capture, the final frame versus settled Gu differs at 45,492 pixels. See [frame 7](transitions/idle-feng_to_gu-07.png) and [after](transitions/idle-feng_to_gu-after.png). Running/Hover entries end on the same frame 7 before handing off to their respective Gu state.
- **V-06, P2 — abrupt blue effect energy/scale step.** In Gu→Feng frame 1→2→3, the electric halo expands abruptly to near the window margins; the character also grows as intended. It does not crop in this 256×256 test viewport (frame-2 alpha bbox `[32,16,474,458]` at 2×). Whether that effect jump is artistically acceptable requires human approval; *the observation* is the abrupt change, not a claim of broken clipping. Feng→Gu frame 7 retains small trailing sparks that disappear on handoff.
- **V-07, P2 — configured-versus-observed dwell mismatch in this environment.** Main-process transition timer requests 140 ms. The separate ungated QA2 pass yielded Gu→Feng renderer event intervals of 217–234 ms and Feng→Gu intervals of 233–234 ms; last-frame-to-completion was 153/155 ms. This measures app events on the current Mac, not actual optical frame onset on an external display. Attribution to renderer scheduling/display throttling is **HYPOTHESIS** until instrumented more precisely.

All 10 and 8 frames were painted in order in all six gated scenarios. The last frame was emitted before transition completion and target form took over. There was no visible window-edge clipping in the captured 2× sheets. Continuous/reversed operations and time-scheduler races are treated in the consolidated audit, not inferred from these single-direction runs. No frozen transition frame was edited.
