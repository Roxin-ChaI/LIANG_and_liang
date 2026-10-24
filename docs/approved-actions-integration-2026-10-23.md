# Approved action integration — 2026-10-23

User authorized unified integration, explicitly deferring Feng Look.

## Asset assembly

Two derived, lossless atlases in
`assets/rework/v0.1.0/approved-actions-integration-2026-10-23/` replace only:

| Form | Zero-based row | Approved source |
|---|---|---|
| Gu | 1 / 2 | Right revision-2 / left suspended sway |
| Feng | 1 / 2 | Approved eight-frame right R2 / exact left mirror |
| Feng | 3 | R2 Waving edge cleanup |
| Feng | 5 | Failed R3 nod-revision |
| Feng | 8 | R2 Review edge cleanup |

All source approvals and hashes are checked before assembly. Every replaced cell
is byte-identical RGBA after decoding the lossless WebP. Every other row remains
identical to the previously selected October 2 atlas, including both forms' Look.
Frozen source atlases and both transitions remain unchanged. Provenance and hashes
are in `manifest.json`; per-action GIFs show the exact integrated cells.

The existing Gu Waiting/Running/Review rows contain semi-transparent pixels;
both baseline atlases also contain an Idle slot 6 unused by the six-frame runtime.
These pre-existing details are preserved, not silently cleaned or newly declared
binary-alpha/empty. The scoped validator permits that specific unused Idle slot;
all new rows have binary alpha, transparent RGB zero and empty spare cells.
This is not a claim of a full clean-atlas validator certification.

Historical approval manifests retain their pre-integration `runtimeIntegrated`
fields as frozen evidence. This document and the new integration manifest track
the subsequent deployment separately.

## Runtime selection and acceptance

Completed on 2026-10-24: asset-overrides selects the two derived atlases.
Only those two entries changed; `previous-asset-overrides.json` preserves the
previous configuration byte-for-byte. Historical asset-production tests now
check that archived configuration and continue checking artwork at original paths.
An additional integration test constrains the live configuration diff to exactly
those two atlas entries. No historical approval or source manifest was rewritten.

Feng artwork timing now follows approved previews: walking 140ms per frame,
Waving/Review 180ms per frame, Failed 280/140/160/160/260/180/160/400ms.
Gu drag remains 120ms per frame. Renderer supplies the active form to frameAt;
priority, transitions, Scheduler and Hooks are unchanged. Look stays untouched.

## Build and live verification

Local build: `dist/Liang no Henshin Integrated 2026-10-24.app`.
43 bundled inputs matched their selected sources, including exact atlas bytes.
Project-owned ad-hoc signing and strict codesign verification passed.
The pre-existing `dist/Liang no Henshin.app` was not overwritten or stopped.

`tools/run_standalone_app_qa.py` returned `STANDALONE_APP_QA_PASS`:

- Real Electron startup, transparent capture margins and 192×208 hitbox.
- Gu→Feng renderer frames 0–9 and Feng→Gu 0–7, correct form takeover and Running restoration.
- Hover, drag row selection, work rows and unchanged Look row routing.
- Injected Beijing boundary schedule and restart reconciliation.
- Synthetic pointer drag only, not physical mouse acceptance.

`tools/qa_integrated_actions.py` returned `SEVEN_ACTIONS_RENDERER_PASS`:
Gu left/right and Feng left/right/Failed/Waving/Review each reported all required
frame indices in a real packaged renderer. Captures were checked for transparent
margin/non-clipping; sampled screenshots were visually inspected. This is not
a claim of exhaustive transition-by-transition visual approval.

Evidence (local generated, not committed):

- `standalone-app/evidence/approved-actions-2026-10-24/report.json` and transition captures.
- `standalone-app/evidence/integrated-seven-actions-2026-10-24/report.json`,
  `events.json`, and seven action screenshots.

Both test runs used temporary profiles, disabled Codex event attachment and exited
their own test processes. Existing App and receiver were not stopped. No Codex
installation/configuration changes, no source art changes, no release tag.
Physical mouse acceptance: NOT_VERIFIED. New-package live Hook acceptance:
NOT_TESTED; isolated tests deliberately avoid competing for the current receiver.

Regression: 108 scoped Python tests passed; all 43 standalone Node tests passed.
Node socket tests needed unsandboxed execution after an EPERM sandbox failure.
This is not the full legacy Python project suite. `git diff --check` passed.

Integration status: ready for user testing of the new separate App. Source/runtime
selection is updated; the previously running packaged App remains its older version
until the user switches to this new build.
