# Build 8881 Dual-Atlas Patch Dry Run

## Result

`BUILD_8881_DUAL_ATLAS_DRY_RUN_PASS`

The run was read-only with respect to ChatGPT.app. Original and patched chunk
copies existed only in a uniquely created system temporary directory and were
removed before the script exited.

## Build and original fingerprints

| Target | Observed value | Gate |
| --- | --- | --- |
| Version | `26.908.40834` | PASS |
| Build | `8881` | PASS |
| `app.asar` SHA256 | `bb40cd8811887363104a19291346af9595632e0e956316a1086b274fb8e3eafc` | PASS |
| Main chunk SHA256 | `0765260be74e8843630d5a92e30bca574783892688e67180c119a5c58679bb61` | PASS |
| Core renderer chunk SHA256 | `737070f94a072d2b4ede9f326e3e1c4142fb82198961251c2e70479b3f926275` | PASS |
| Overlay chunk SHA256 | `9ddf6ce3bb7a6b2276d2b598afc3bb14f3424e5b4d1bb452378d5fbe0dfa5f49` | PASS |

The script blocks before patch-site analysis when any gate differs. It does not
attempt version adaptation.

## Patch targets and anchors

| Layer | Target | Composite stable anchors | Patch-site matches |
| --- | --- | --- | ---: |
| Main | Custom-avatar service in `.vite/build/main-DaMR-wdT.js` | Service class shape, `customAvatars` registration, `loadAvatar` delegation, and spritesheet result field | 1 |
| Core/model | Avatar option model in `webview/assets/app-initial-9b95fa538c62.js` | `Alo` definition/export, renderer export, full nine-state map, Pet state data attribute, and native spritesheet mapping | 1 |
| Overlay | Source argument in `webview/assets/avatar-overlay-native-page-bb89afb2a8f6.js` | `kd` selected-avatar hook, custom by-ID query alias, imported `Alo` alias, drag-state context, and source call | 1 |

Hashed filenames and minified symbols are never used alone. The exact build
fingerprints and the complete anchor groups must all match.

## Prototype operations

The main temporary copy preserves the native `spritesheetDataUrl` result and
adds propagation slots for `runtimeForms` and `runtimeInitialForm`. The core
temporary copy preserves the single-atlas option field while carrying those
optional dual-form fields into the resolved avatar option.

The overlay temporary copy selects a preloaded form source when `runtimeForms`
is present, uses the sidecar initial form for this dry run, and otherwise falls
back to the original single-atlas source. The existing `Alo` conversion,
mascot component, renderer, task-state map, and Pet ID remain in the path.

This static injection complements the executable project-side prototypes:
the loader proves that both formal atlases can be loaded once, and the source
registry proves that committed form changes can select those in-memory data
URLs while incrementing `playbackEpoch` without another disk read or query
refresh.

## Validation

- Original chunks extracted to system temp: PASS
- Main patch-site unique: PASS (1)
- Core/model patch-site unique: PASS (1)
- Overlay patch-site unique: PASS (1)
- Native single-atlas fallback retained: PASS
- Dual-atlas propagation branch present: PASS
- Initial-form source-selection branch present: PASS
- All three patched temporary JavaScript copies pass `node --check`: PASS
- Post-patch anchors remain identifiable: PASS
- Original version, build, ASAR/chunk hashes, ASAR size, mode, and mtime unchanged: PASS
- Original `app.asar` SHA unchanged: PASS
- Temporary original and patched copies removed: PASS
- Proprietary Codex chunks stored or committed in the repository: none

## Limitations

This is a static dry run, not an installed runtime patch. It does not modify or
launch ChatGPT.app, load a sidecar inside Electron, add overlay controls, wire
`setForm`, implement transitions, choose a bridge transport, call private IPC,
install a scheduler, or measure renderer texture memory. The injected main
shape propagates optional dual-form data; the pure Node loader remains the
executable proof of sidecar parsing, containment, atlas validation, and
one-time reads.

The procedure is valid only for the exact recorded build fingerprints. Any
Desktop update or local bundle change requires a fresh recon and must fail the
current gate closed.
