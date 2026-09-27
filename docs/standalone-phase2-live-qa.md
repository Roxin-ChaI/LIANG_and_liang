# Standalone Phase 2 — Desktop Hook live QA

Date: 2026-09-27 (Asia/Shanghai). The official Codex App, its Hook definition,
and user-level configuration were not edited. Project Hook definition SHA256:
`22de678d81469f0ccb2c74181e36f7404f773b7eaf1d2efb916c53bbcc40e84f`.

Tested project-owned App: `dist/Liang no Henshin Phase2 Live Preloaded.app`
(37 bundled source/asset files, own `com.liang-no-henshin.standalone` Bundle ID).
Final matching-source build: `dist/Liang no Henshin Phase2 Final.app`.
The only later code adjustment classifies an internal timeout as `hook-timeout`
instead of a real `hook-event`; its packaged full-window QA passed.
The live runner used a temporary App profile and accepted only the known real
Desktop session `01a0dd5b-0416-7ed0-986b-edf5d6dbc0b9`; it did not inject
Hook events. Its event and report artifacts remain untracked under
`standalone-app/evidence/live-desktop-hook-qa-3/`.

| Check | Result | Evidence |
| --- | --- | --- |
| `PreToolUse` → Running | PASS | Hook 07:37:30.834 UTC; renderer row 7 within 51 ms |
| `PostToolUse` | PASS | Work state stayed Running until `Stop` |
| Gu → Feng | PASS | Renderer reported transition frames 0–9, then Feng with Running restored |
| Feng → Gu | PASS | Renderer reported transition frames 0–7, then Gu with Running restored |
| `Stop` → Idle | PASS | Hook 07:38:07.582 UTC; renderer row 0 within 52 ms |
| Real pointer drag | PASS in separate same-build window | macOS UI pointer drag moved window x=300 → 325; App emitted `running-right`; no synthetic drag command was used |
| Desktop restart | PASS | New post-restart Desktop session and real `sleep 10` Hook/Renderer trace below |

An earlier live attempt exposed missing first-play Gu→Feng frames 1 and 2.
The standalone renderer was decoding transition PNGs for the first time while
the main-process 140 ms timer advanced. The App now decodes all 18 existing
overlay frames before startup; neither approved image pixels nor frame order
changed. The subsequent real Desktop run rendered all 10 and 8 frames.

The original live runner timed out before the separate physical drag and marks
that subcheck `NOT_VERIFIED` in its own generated JSON. The separate macOS UI
drag above supplies that check; the generated JSON is intentionally not altered.
The initial timeout and first-play skipped-frame logs are retained in ignored
evidence folders, not promoted to PASS.

`UserPromptSubmit` and `PermissionRequest` are not used by the adapter because
they were not observed in prior Desktop verification. Waiting/Review/Failed
live event mapping is NOT_VERIFIED and is not claimed here.

Regression at original Phase 2 acceptance: Python `263 passed, 12 subtests passed`;
Node `180 passed`.
Final bundled App window QA: `STANDALONE_APP_QA_PASS` at
`standalone-app/evidence/phase2-final-bundled/report.json`. The default
sandbox rejected unrelated test Unix socket binds; the identical full suites
passed with local socket permissions. No CLI events or synthetic replay results
were substituted for the live Desktop checks above.

## Post-restart final acceptance

On 2026-09-27, after the user restarted Codex Desktop, the official Desktop
main process was observed as PID `26113`, started at 18:11:30 Asia/Shanghai.
A newly created project Desktop session `01a0e303-07b0-7e50-91fb-ba306bb07db0`
emitted `SessionStart` at 13:17:22.010 UTC, after that process start. This is
not the earlier Phase 2 QA session. The session's Desktop command record shows
`/bin/zsh -lc 'sleep 10'`, exit 0, duration 9,888 ms; no CLI or injected Hook
event was used.

The tested binary was the later project-owned Running fix build,
`dist/Liang no Henshin Running Fix.app`. A temporary userData profile filtered
only this new Desktop session so the observing session's own tools could not
mask `Stop → Idle`. The receiver and Electron each had one Unix socket listener.
The trace file is the metadata-only
`/tmp/lnh-phase2-restart-oPG4ao/user-data/hook-pipeline.jsonl`.

| Fresh event (UTC) | Actual renderer/task result | Hook → renderer latency |
| --- | --- | --- |
| `PreToolUse` 13:21:28.970 | Running row 7 at 13:21:29.008 | 38 ms |
| `PostToolUse` 13:21:39.031 | Active sessions stayed 1; Running row 7 remained | No Idle transition |
| `Stop` 13:21:43.938 | Active sessions became 0; Idle row 0 at 13:21:43.991 | 53 ms |

The Python receiver recorded successful forwarding of all three events. The
post-restart full regression passed: Python `265 passed, 12 subtests passed`;
Node `183 passed`. The authorized Hook definition SHA256 remained
`22de678d81469f0ccb2c74181e36f7404f773b7eaf1d2efb916c53bbcc40e84f`.
The earlier generated JSON reports retain their historical
`RESTART_NOT_VERIFIED` value; this later, directly observed result supersedes
that historical status without rewriting prior evidence.
