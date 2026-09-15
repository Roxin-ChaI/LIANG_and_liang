# Build 9275 Transition Overlay Runtime Prototype (Phase 3F)

Phase 3F is a project-owned deterministic player, structural renderer plan,
visual QA sheet, and **temporary-copy-only** Build 9275 injection dry-run. It
does not install a patch or establish that Codex Desktop has played a custom
transition. Formal Gu/Feng atlases and all frozen PNG frames are unchanged.

## Fingerprint and Scope

| Item | Read-only value |
| --- | --- |
| App version/build | `26.908.70816 / 9275` |
| Real `app.asar` SHA256 | `100b3a06768326eec58ae32e54fa7b85368fef8d4ead5a5866ecb0e8751bdeaa` |
| Main service | `.vite/build/main-DaMR-wdT.js` |
| Native metadata loader | `.vite/build/src-CCXHtyvY.js` |
| Core Pet renderer | `webview/assets/app-initial-4d7ea7f81c2d.js` |
| Native overlay | `webview/assets/avatar-overlay-native-page-efa96d74af15.js` |
| Mascot | `webview/assets/avatar-mascot-button-7a295935c1d3.js` |

The dry-run gates on this version/build/ASAR SHA and all seven key chunk
SHA256 values recorded in `docs/runtime-recon-build-9275.md`. A mismatch
terminates as `BUILD_9275_FINGERPRINT_MISMATCH` before extraction or patch
operations. It writes only the main, core, and overlay copies to one system
temporary directory. It never writes to `/Applications/ChatGPT.app`, signs
anything, changes `~/.codex`, opens a private socket, or executes a Codex
module.

## Patch Sites and Match Counts

All eight Phase 3E composite locators were re-run against the current
archive during the Phase 3F dry-run:

| Site | Matches | Temporary architecture |
| --- | ---: | --- |
| Dual-form result | 1 | Main native `loadAvatar` delegation is retained; a conditional result branch recognizes two already-loaded form URLs. |
| Hot source | 1 | Overlay source conversion can select the committed form URL from a preloaded registry. |
| Descriptor | 1 | Core retains the native nine-state table and adds a separate arbitrary-frame one-shot descriptor branch. |
| Completion | 1 | Core native finite/idle completion remains; the one-shot branch invokes a token-guarded completion hook at the final duration boundary. |
| Transition owner | 1 | Project state tracks current/target form, operation token, frame index, playback epoch, and latest underlying task state. |
| Atomic form commit | 1 | Committed form/source/epoch update together after active-token completion. |
| Oversized sibling | 1 | A transition-only image is a sibling of the normal clipped root at its outer layout wrapper. |
| Clipping boundary | 1 | Normal root `overflow-hidden` is retained; the sibling is outside it. |

This is a **structural injection proof**, not a running-app proof. The
temporary branches are deliberately dormant unless the loader supplies both
validated atlas URLs and transition frame URLs. The Phase 2 project loader
demonstrates load-once behavior, but Phase 3F does not patch the native loader
or install reactive state plumbing.

## Project-Side Playback and Overlay Contract

`runtime-patch/prototype/transition-assets.mjs` loads the 18 formally frozen
oversized RGBA PNGs and their SHA manifest in exact order once. The player is
I/O-free thereafter. Gu→Feng displays all 10 frames once; Feng→Gu displays
all 8 once. Frame 0 and the last frame each occupy their full 140 ms. Only
the active operation token can commit; duplicate requests preserve progress,
reverse requests invalidate the old token, and stale completion is ignored.
Task state can update underneath the transition. Reduced motion commits
immediately. Missing target atlas rejects; invalid transition assets fall
back to an immediate form commit.

`runtime-patch/prototype/transition-overlay.mjs` keeps a normal `192×208`
container at `(0,0)`, Pet ID `custom:liang-no-henshin`, and a marked
`192×208` drag hitbox. Only the character visual may be hidden during
transition; the normal container and drag coordinate system remain. The
oversized frame is an absolute, pointer-events-none sibling outside the
normal clipped root. Frozen anchor offsets are computed as
`left=96-anchorX`, `top=203-anchorY`: Gu→Feng `224×240` at `(-16,-18)`;
Feng→Gu `208×224` at `(-9,-14)`. After one-shot completion, the sibling is
removed and the target's preloaded atlas source takes over normal rendering
with incremented playback epoch. There is no Settings Refresh call in the
project-side prototype.

The two deterministic nearest-neighbor QA sheets show the initial idle,
every transition frame, and target idle, with normal-box, oversized-canvas,
anchor, and baseline guides:

- `hatch-runs/transition-qa/overlay/gu-to-feng-overlay-sequence.png`
- `hatch-runs/transition-qa/overlay/feng-to-gu-overlay-sequence.png`

## Verification Results

| Check | Result |
| --- | --- |
| Player tests | `24/24 PASS` |
| Overlay render-plan tests | `17/17 PASS` |
| Complete runtime/dual-atlas/source/player/overlay regression | `94/94 PASS` after dry-run |
| Frozen oversized asset validator | `PASS`, 18 frames, `effect_crop_count=0` |
| Gu→Feng / Feng→Gu reference simulations | `PASS`, 10/10 and 8/8; target form takes over |
| Reverse/cancel/stale-token simulation | `PASS`, remains Gu, epoch unchanged |
| Temporary main/core/overlay JS parser | `node --check PASS` for all three patched copies |
| Static native-map/look-row/single-atlas/clipping/hitbox assertions | `PASS` |
| Real ASAR and seven key chunk hashes before/after | `UNCHANGED` |
| Proprietary original/patched temporary copies | `CLEANUP PASS` |

## Remaining Risk and Exit Boundary

The outer sibling avoids the normal `<main>` DOM clipping without changing
its `overflow-hidden` class or expanding the mascot hit region. **UNKNOWN**
until a future authorized live visual test: whether the overlay window crops
an oversized frame at physical screen edges and whether the current layout
object provides the exact mascot origin assumed by the temporary sibling
sketch. **UNKNOWN** until real patch preparation: native loader wiring for
the two atlases and standalone frames, reactive renderer invalidation after
`setForm`, and subscription/timer wiring between the one-shot state and
overlay. The temporary code's syntax success must not be presented as
functional Codex Desktop playback. The installed App also has the preexisting
invalid-signature verification warning; Phase 3F performs no signing.

Project-side technical prototype status: `TRANSITION_RUNTIME_POC_PASS` if
the final full regression and integrity checks pass. Visual acceptance is
**not** self-approved: `VISUAL_REVIEW_REQUIRED=true`. No real App patch,
bridge, scheduler, daemon, or time-controller integration follows without
user review and a separate authorization.
