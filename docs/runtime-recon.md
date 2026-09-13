# Codex Pet Runtime Recon

Evidence in this document was collected read-only from the locally installed
`/Applications/ChatGPT.app`. Status labels describe the strength of each
finding: `CONFIRMED`, `LIKELY`, or `UNKNOWN`.

## Current Desktop Build

- **CONFIRMED** — Bundle path: `/Applications/ChatGPT.app`.
- **CONFIRMED** — `CFBundleIdentifier`: `com.openai.codex`.
- **CONFIRMED** — `CFBundleShortVersionString`: `26.908.40834`.
- **CONFIRMED** — `CFBundleVersion`: `8881`.
- **CONFIRMED** — Product package metadata names the application
  `openai-codex-electron`, version `26.908.40834`, build flavor `prod`, and
  Electron dependency `42.3.0`.
- **CONFIRMED** — Main executable:
  `/Applications/ChatGPT.app/Contents/MacOS/ChatGPT`.
- **CONFIRMED** — The main executable is a thin 64-bit `arm64` Mach-O. The
  bundle also declares `LSRequiresNativeExecution=true`.
- **CONFIRMED** — Embedded signing metadata reports identifier
  `com.openai.codex`, team identifier `2DC432GLL2`, hardened-runtime flag,
  CDHash `66d1d185c8870f38e19fb698b031fe9d9ba2afb7`, and a stapled notarization
  ticket.
- **CONFIRMED** — Strict deep verification currently fails with
  `invalid signature (code or signature have been modified)` for `arm64`.
  This is the state of the inspected installation; it is not evidence of which
  operation changed the bundle.

## App Bundle Layout

- **CONFIRMED** — Approximate disk usage is 1.3 GB for the application,
  981 MB for `Contents/Resources`, and 360 MB for `Contents/Frameworks`.
- **CONFIRMED** — The top-level executable is the 68 KB Electron launcher.
- **CONFIRMED** — `Contents/Resources/app.asar` is the primary application
  archive (307 MB); its header indexes 9,144 files.
- **CONFIRMED** — `Contents/Resources/app.asar.unpacked` contains unpacked
  JavaScript and native dependencies, including `better-sqlite3`, `node-pty`,
  and `objc-js`.
- **CONFIRMED** — `Contents/Resources/native` contains additional `.node` and
  helper binaries. No Pet-specific native module was identified by filename.
- **CONFIRMED** — The Chromium/Electron runtime is under
  `Contents/Frameworks/Codex Framework.framework`, version `152.0.7977.83`.
- **CONFIRMED** — Sparkle is bundled separately under
  `Contents/Frameworks/Sparkle.framework`.
- **CONFIRMED** — No source-map file (`*.map`) is present in the ASAR index.

## Runtime Packaging

- **CONFIRMED** — The desktop application is an Electron application whose
  package entry point is `.vite/build/early-bootstrap.js` inside `app.asar`.
- **CONFIRMED** — Electron main-process code is emitted as minified Vite
  bundles under `.vite/build/`, principally `main-DaMR-wdT.js`.
- **CONFIRMED** — Preload code is emitted under `.vite/build/preload.js` and
  `.vite/build/browser-page-preload.js`.
- **CONFIRMED** — Renderer code is emitted as minified, content-hashed chunks
  under `webview/assets/`. Pet code is present in renderer chunks, not in an
  identifiable Pet-specific native module.
- **CONFIRMED** — High-signal renderer chunks include
  `app-initial-9b95fa538c62.js`,
  `avatar-overlay-native-page-bb89afb2a8f6.js`,
  `avatar-mascot-button-c97748e2485e.js`, and
  `pets-settings-route-833ea8d5b367.js`.

## Search Anchors

The following anchors were found by scanning the current ASAR without
extracting or changing the application:

| Anchor | Confirmed locations or observation |
| --- | --- |
| `custom-avatars` | `webview/assets/app-initial-9b95fa538c62.js` |
| `cloud-pets` | `webview/assets/app-initial-9b95fa538c62.js` |
| `selected-avatar-id` | `.vite/build/src-CCXHtyvY.js`, `.vite/build/worker.js`, `webview/assets/app-initial-9b95fa538c62.js`, `webview/assets/src-996ff3571e1f.js` |
| `spritesheet` / `spriteVersionNumber` | `.vite/build/main-DaMR-wdT.js`, `webview/assets/app-initial-9b95fa538c62.js`, and Pet-specific renderer chunks |
| `loadAvatar` | `.vite/build/main-DaMR-wdT.js`, `webview/assets/app-initial-9b95fa538c62.js` |
| `first-awake` | `webview/assets/app-initial-9b95fa538c62.js`, `webview/assets/avatar-overlay-native-page-bb89afb2a8f6.js`, `webview/assets/src-996ff3571e1f.js` |
| `waving` / `jumping` | `webview/assets/avatar-mascot-button-c97748e2485e.js`; also present in the main renderer bundle |
| `waiting` / `running` / `review` / `failed` | `webview/assets/avatar-overlay-native-page-bb89afb2a8f6.js`; also present in the main renderer bundle |
| `Refresh` | `.vite/build/main-DaMR-wdT.js`, `webview/assets/app-initial-9b95fa538c62.js`, `webview/assets/pets-settings-route-833ea8d5b367.js` |

Common English terms such as `running`, `review`, `failed`, and `Refresh`
occur throughout unrelated product code. Their presence is treated as a useful
anchor only when it appears in one of the Pet-specific chunks above.

## Stable Build Fingerprint

The preferred build identity is the version/build tuple plus hashes of the
actual executable and current ASAR. Smaller Pet-related chunk hashes provide
more focused runtime anchors.

| Artifact | SHA256 |
| --- | --- |
| `Contents/MacOS/ChatGPT` | `83750779e2f5a040cc05f6b05486e3bfa371ff19cb9edcd6102140b369c67683` |
| `Contents/Resources/app.asar` | `bb40cd8811887363104a19291346af9595632e0e956316a1086b274fb8e3eafc` |
| `.vite/build/main-DaMR-wdT.js` | `0765260be74e8843630d5a92e30bca574783892688e67180c119a5c58679bb61` |
| `.vite/build/preload.js` | `9dba229e0b3cfa1cc9a7e78925b5f168b7f7385e1c18d785d13ce8e823e65207` |
| `webview/assets/app-initial-9b95fa538c62.js` | `737070f94a072d2b4ede9f326e3e1c4142fb82198961251c2e70479b3f926275` |
| `webview/assets/avatar-overlay-native-page-bb89afb2a8f6.js` | `9ddf6ce3bb7a6b2276d2b598afc3bb14f3424e5b4d1bb452378d5fbe0dfa5f49` |
| `webview/assets/avatar-mascot-button-c97748e2485e.js` | `ee33fdf319c66b74b467ae7927fe7948b4a59014c4015c82f63d3ad9378ba227` |
| `webview/assets/pets-settings-route-833ea8d5b367.js` | `1327c7ff92df427d6fff259837152e64182c426938121a0becb7b8fd23048fd6` |

- **CONFIRMED** — `Info.plist` declares ASAR integrity SHA256
  `517e720853645405849b726c8e32862c020154780d0c319d8df44b88d84086f1`.
- **CONFIRMED** — The declared ASAR integrity hash differs from the current
  ASAR SHA256 above. Together with failed strict code-signature verification,
  this means Phase 1 must not assume the inspected bundle is byte-identical to
  the originally signed distribution.

## Custom Pet Loading

- **CONFIRMED** — The local manifest schema is bundled in
  `.vite/build/src-CCXHtyvY.js`. It accepts optional `id` and `displayName`, a
  nullable `description`, `spriteVersionNumber` restricted to `1 | 2` with a
  default of `1`, and `spritesheetPath` with a default of
  `spritesheet.webp`.
- **CONFIRMED** — The loader resolves Codex home from `CODEX_HOME`, or from
  `<home>/.codex` when that environment variable is absent. It scans both the
  legacy `avatars/<name>/avatar.json` location and the current
  `pets/<name>/pet.json` location. Entries from `pets` replace a same-ID legacy
  entry, and returned IDs use the `custom:<directory-name>` form.
- **CONFIRMED** — Manifest and spritesheet paths are resolved through a
  containment check. Absolute paths and paths that resolve to the parent of or
  outside the pet directory are rejected.
- **CONFIRMED** — The loader reads the selected image bytes on every actual
  `load` or `loadAvatar` invocation, recognizes PNG or WebP from their headers,
  and requires `1536x1872` for sprite version 1 or `1536x2288` for sprite
  version 2. Invalid JSON, paths, formats, or dimensions cause that entry to be
  omitted or returned as `null`.
- **CONFIRMED** — A successful load returns metadata plus a base64
  `spritesheetDataUrl`; the renderer therefore does not retain a live file URL
  to the installed atlas.
- **CONFIRMED** — The Electron main bundle registers an `iR` service instance
  as `customAvatars`. Its `load()` and `loadAvatar(id)` methods delegate to the
  shared loader functions exposed from `.vite/build/src-CCXHtyvY.js`.
- **CONFIRMED** — Renderer initialization creates a service proxy named `Iq`;
  local avatar queries call `Iq.customAvatars.load()` and
  `Iq.customAvatars.loadAvatar(id)` rather than reading the filesystem in the
  renderer.
- **LIKELY** — The service proxy is carried over the app's generic renderer to
  main request transport. The preload exposes that transport as
  `window.electronBridge.sendMessageFromView`, backed by
  `ipcRenderer.invoke("codex_desktop:message-from-view", ...)`.
- **UNKNOWN** — Minification and the absence of shipped source maps prevent a
  reliable name-level attribution of the exact generic RPC envelope used for
  the `customAvatars` call without instrumenting the application. No such
  instrumentation was performed.

The current local query definitions in
`webview/assets/app-initial-9b95fa538c62.js` are:

| Query | Key | Relevant policy |
| --- | --- | --- |
| **CONFIRMED** local list (`Luo`) | `["custom-avatars"]` (`Iuo`) | `staleTime: Infinity`; no refetch on mount or window focus |
| **CONFIRMED** local avatar by ID (`Ruo`) | `["custom-avatars", "by-id", id]` | enabled only for `custom:` IDs; `gcTime: 0`; `staleTime: Infinity`; no window-focus refetch; no retry |
| **CONFIRMED** cloud list | prefix `["cloud-pets", "list"]` (`kuo`) | five-minute stale/refetch interval and window-focus refetch |
| **CONFIRMED** cloud selection | prefix `["cloud-pets", "selection"]` (`ldo`) | one-minute stale/refetch interval and window-focus refetch |

## Refresh Call Chain

The following call chain is **CONFIRMED** for the current build:

```text
Settings > Pets > Refresh
  -> settings component onRefreshCustomAvatars handler
  -> invalidate ["custom-avatars"]
  -> invalidate ["cloud-pets", "list"]
  -> invalidate ["cloud-pets", "selection"]
  -> active local list/by-ID queries refetch through Iq.customAvatars
  -> main custom-avatar service re-reads pet.json and spritesheet bytes
  -> new spritesheetDataUrl enters the resolved avatar option
  -> overlay receives a new renderer source
  -> CSS background-image uses the new data URL
```

- **CONFIRMED** — The Refresh button in
  `pets-settings-route-833ea8d5b367.js` calls a handler that invalidates the
  three query prefixes above. Query invalidation is prefix-based, so
  invalidating `["custom-avatars"]` also reaches the current
  `["custom-avatars", "by-id", id]` query.
- **CONFIRMED** — The local list and by-ID queries otherwise remain fresh
  indefinitely and opt out of focus-based refetch. Replacing
  `spritesheet.webp` on disk alone consequently does not change the cached
  base64 data URL.
- **CONFIRMED** — The effective update boundary is the by-ID query refetch and
  resulting `spritesheetDataUrl` replacement, not the Settings view itself.
- **UNKNOWN** — No filesystem watcher for custom-pet manifests or atlas files
  was identified in the inspected Pet paths. This recon does not prove that no
  unrelated app subsystem could observe those files.

## Overlay Avatar Loading

The following selected-avatar chain is **CONFIRMED**:

```text
selected-avatar-id
  -> overlay selected-avatar hook
  -> kd() resolves built-in vs custom: vs pet_
  -> Ruo custom by-ID query for custom:<id>
  -> Iq.customAvatars.loadAvatar(id)
  -> validated spritesheetDataUrl
  -> resolved avatar option
  -> Alo() converts it to { petId, spriteRowCount, spritesheetUrl }
  -> avatar overlay -> mascot button -> core Pet renderer
  -> background-image: url(<spritesheetDataUrl>)
```

- **CONFIRMED** — `kd()` in
  `avatar-overlay-native-page-bb89afb2a8f6.js` obtains the selected option and
  `selectedAvatarId`, runs the custom by-ID query for `custom:` IDs or the
  cloud lookup for `pet_` IDs, and temporarily returns a null avatar when the
  selected remote/custom value is still being fetched with no cached data.
- **CONFIRMED** — Built-in IDs bypass both lookups. Custom and cloud results
  are merged back into the normal avatar-option model before rendering.
- **CONFIRMED** — `Alo()` in `app-initial-9b95fa538c62.js` converts an option
  with artwork into `{petId, spriteRowCount, spritesheetUrl}`. Version 1 maps
  to 9 rows and version 2 maps to 11 rows. Built-ins instead use `assetRef`.
- **CONFIRMED** — The overlay component chain ends at the exported mascot
  button and core renderer (`Uw`; minified implementation symbol `ruo`). The
  renderer sets `backgroundImage` from `source.spritesheetUrl` and sets
  `backgroundSize` to eight columns by the source row count.

## Animation State Machine

- **CONFIRMED** — The v2 layout constant in
  `app-initial-9b95fa538c62.js` is `1536x2288`, 8 columns by 11 rows, with
  `192x208` cells and required row frame counts
  `[6, 8, 8, 4, 5, 8, 6, 6, 6, 8, 8]`.
- **CONFIRMED** — The core renderer selects a frame by converting its column
  and row to CSS `background-position`. Changing `state`, `lookFrame`, reduced
  motion, or source row count restarts its timer effect.
- **CONFIRMED** — With reduced motion enabled, any state is held on its first
  frame. With normal motion, idle uses the six idle frames at six times their
  base duration and loops indefinitely.
- **CONFIRMED** — Every non-idle state is expanded to exactly three copies of
  its row animation. After the third copy, playback enters the six-times-slow
  idle sequence and loops there. The owning task/notification state may still
  be active, but the animation does not replay until a relevant renderer prop
  changes.

| State | Row | Frames | One row pass | Normal completion |
| --- | ---: | ---: | ---: | --- |
| **CONFIRMED** `idle` | 0 | 6 | base 1100 ms; rendered slow pass 6600 ms | slow idle loops |
| **CONFIRMED** `running-right` | 1 | 8 | 1060 ms | 3 passes, then slow idle |
| **CONFIRMED** `running-left` | 2 | 8 | 1060 ms | 3 passes, then slow idle |
| **CONFIRMED** `waving` | 3 | 4 | 700 ms | 3 passes, then slow idle |
| **CONFIRMED** `jumping` | 4 | 5 | 840 ms | 3 passes, then slow idle |
| **CONFIRMED** `failed` | 5 | 8 | 1220 ms | 3 passes, then slow idle |
| **CONFIRMED** `waiting` | 6 | 6 | 1010 ms | 3 passes, then slow idle |
| **CONFIRMED** `running` | 7 | 6 | 820 ms | 3 passes, then slow idle |
| **CONFIRMED** `review` | 8 | 6 | 1030 ms | 3 passes, then slow idle |

- **CONFIRMED** — The idle base frame durations are
  `280, 110, 110, 140, 140, 320` ms. Slow idle multiplies each by six.
- **CONFIRMED** — `running-left` and `running-right` use 120 ms per ordinary
  frame and 220 ms for their last frame. `waving` and `jumping` use 140 ms per
  ordinary frame and 280 ms for their last frame. `failed` uses 140/240 ms;
  `waiting` uses 150/260 ms; `running` uses 120/220 ms; and `review` uses
  150/280 ms.
- **CONFIRMED** — Hover is implemented in the mascot button. Pointer enter
  changes the effective state to `jumping`; pointer leave restores the
  underlying notification state. Either change restarts playback.
- **CONFIRMED** — Drag is a higher-priority transient state supplied by the
  overlay. During a non-orb drag, an incremental horizontal movement of at
  least 4 screen pixels selects `running-right`; at most -4 selects
  `running-left`. Drag start, release, and cancellation clear the transient
  state.
- **CONFIRMED** — The highest-priority visible notification maps to the mascot
  state: a loading notification selects `running`; warning selects `waiting`;
  danger selects `failed`; success selects `review`; and informational or no
  notification selects `idle`.
- **CONFIRMED** — A `first-awake` notification maps to `waving`, expires after
  8 seconds, and is suppressed once its avatar ID is recorded under
  `first-awake-pet-notification-avatar-ids`. Refreshing artwork for the same
  selected avatar ID is therefore not a dependable greeting retrigger.
- **CONFIRMED** — Look direction is enabled only for sprite version 2. Cursor
  direction is quantized to the nearest of 16 angles at 22.5-degree steps;
  directions 0-7 use row 9 and directions 8-15 use row 10. A one-pixel radial
  dead zone returns no look frame. The mascot button forwards look frames only
  while its effective state is `idle`, `running`, or `waving`.
- **LIKELY** — Mouse enter/leave can appear to retrigger `running` or another
  notification-backed row because entering starts `jumping` and leaving
  restores the still-current backing state, causing the renderer timer effect
  to start that row again.

## Dual-Form Patch Point

- **CONFIRMED** — The current avatar model carries exactly one
  `spritesheetDataUrl`/`spritesheetUrl` per avatar option. The core renderer can
  render any supplied URL but has no `gu`/`feng` concept.
- **LIKELY** — Holding both forms under one Pet ID requires a small vertical
  model extension, not a frame-rendering rewrite: extend the manifest/loader
  result to return both validated atlas data URLs, preserve them when local
  options are assembled, and add `form: "gu" | "feng"` at the overlay owner.
- **LIKELY** — The narrowest renderer-side insertion point is immediately
  before the overlay calls `Alo()`/passes `source` to the mascot button. Select
  one cached URL there and keep the existing renderer, state rows, look logic,
  and Pet ID unchanged.
- **LIKELY** — `setForm("gu" | "feng")` can update the overlay-owned form and
  swap the selected source synchronously. Keying the renderer by form, or
  adding the selected source identity to the timer effect dependencies, would
  reset frame selection deterministically without Settings Refresh.
- **UNKNOWN** — The production manifest contract has no dual-atlas field, so
  the precise field spelling and backward-compatible migration policy remain a
  Phase 1 design decision.

## Transition Patch Point

- **CONFIRMED** — The current state map contains only the nine standard rows.
  The renderer exposes neither an arbitrary playback descriptor nor an
  animation-completion callback.
- **CONFIRMED** — Reusing `waving` is not a sound transition trigger: it has a
  fixed four-frame row, repeats three times, falls into slow idle, and its
  `first-awake` trigger is remembered per avatar ID rather than replayed for a
  same-ID artwork refresh.
- **LIKELY** — The least invasive robust extension is an explicit playback
  descriptor accepted by the core renderer: `{source, frames,
  loopStartIndex: null, onComplete}`. Existing named states can continue to be
  generated by the current state map.
- **LIKELY** — The overlay should own a transition value containing direction
  and target form. Its effective priority should be transition, then drag,
  then hover, then notification state. While a transition is active, look and
  hover changes should not replace it.
- **LIKELY** — When the final transition frame's duration elapses, the renderer
  should call `onComplete`; the overlay should atomically set the target form,
  clear the transition, and resume its current normal state. Making the final
  transition frame pixel-identical to the target idle entry frame avoids a
  visual seam.
- **UNKNOWN** — Whether transition artwork should be packed into another
  standards-shaped atlas or exposed as a dedicated strip should be decided
  after a source-build prototype measures the packaging and memory tradeoff.

## Local Control Bridge Candidate

- **CONFIRMED** — The preload already exposes a narrow `electronBridge` through
  Electron `contextBridge`; its renderer-to-main operations use named,
  application-scoped IPC channels. Filesystem access for custom pets already
  resides outside the renderer in the main/service layer.
- **LIKELY** — The best future control boundary is a new, narrowly typed
  preload method backed by a dedicated Electron IPC handler in main. It should
  accept only a validated form enum and transition intent, then notify the
  overlay through the existing application message/service pattern.
- **LIKELY** — The main process should remain authoritative for local control
  input and validation; renderer state should remain authoritative for visual
  sequencing and completion. This avoids granting the renderer generic local
  filesystem or socket access.
- **LIKELY** — If an external controller must connect later, a separately
  authenticated localhost or Unix-domain endpoint owned by the new main
  service is safer than exposing an unrestricted file/event watcher. Its
  messages should still enter through the same typed main-to-renderer event.
- **CONFIRMED** — The existing Codex private IPC socket was not used during
  recon and is not recommended as an integration point.
- **UNKNOWN** — Authentication, lifecycle ownership, and the external endpoint
  type are intentionally deferred until Phase 1 threat modeling.

## Stable Patch Anchors

- **CONFIRMED** — Content-hashed chunk filenames and minified identifiers are
  build-specific and must not be treated as durable names.
- **CONFIRMED** — No shipped source maps are available, despite trailing
  `sourceMappingURL` comments in emitted JavaScript.
- **LIKELY** — The strongest renderer anchors are the combined v1/v2 layout
  constants; the complete nine-state string map; the error text
  `Codex pet animation frame is out of range`; the data attributes
  `data-codex-pet-id` and `data-codex-pet-state`; and exports imported as `Uw`
  and `tT` by adjacent Pet chunks.
- **LIKELY** — Strong loader anchors are the manifest keys
  `spriteVersionNumber` and `spritesheetPath`, the default
  `spritesheet.webp`, dimensions `1536x1872` and `1536x2288`, the `custom:`
  prefix, and the main service property `customAvatars`.
- **LIKELY** — Strong Refresh anchors are the localized description
  `Button label to refresh custom pets from local manifests` and the three
  query prefixes `custom-avatars`, `cloud-pets/list`, and
  `cloud-pets/selection`.
- **LIKELY** — Strong overlay anchors are `first-awake`,
  `first-awake-pet-notification-avatar-ids`, the pointer messages beginning
  `avatar-overlay-drag-`, and the transition from `mascotDragState` to
  `transientState` to `data-codex-pet-state`.

## Risks

- **CONFIRMED** — Direct edits to the installed ASAR would change a signed app
  resource, and the inspected installation already has an ASAR-integrity and
  strict-signature mismatch. This recon does not establish a safe production
  patch procedure.
- **CONFIRMED** — Bundle chunks are minified, content-hashed, and lack source
  maps. A byte or identifier patch would be fragile across Desktop updates.
- **LIKELY** — Holding two base64 atlases plus transition artwork increases
  renderer memory and decode cost. Phase 1 should measure retained image and
  decoded texture memory before finalizing the representation.
- **LIKELY** — A form switch that does not reset or key the animation effect
  can preserve an old row/column position against a new atlas. The source and
  playback state must change as one transaction.
- **LIKELY** — Transition completion can race with hover, drag, notification,
  selected-avatar, and overlay-unmount changes. Completion should carry an
  operation token so stale callbacks cannot switch form.
- **LIKELY** — App updates can replace all content-hashed anchors. Any Phase 1
  compatibility gate must verify bundle version plus the executable, ASAR, and
  focused Pet chunk fingerprints before acting.
- **UNKNOWN** — The cause and history of the current signature/integrity
  mismatch are outside the evidence collected here.

## Phase 1 Recommendation

- **LIKELY** — Proceed only with a controlled source-level or reproducible
  unpack/rebuild prototype against the exact fingerprint recorded above; do
  not begin with ad-hoc edits to the active signed application.
- **LIKELY** — Prototype in this order: dual-atlas loader/model support;
  overlay-owned `form` and immediate `setForm`; arbitrary one-shot playback
  plus completion; then a typed main/preload control method. Verify ordinary
  custom pets remain backward compatible after each step.
- **LIKELY** — Add deterministic tests for manifest containment and dimensions,
  query refresh, source swap, all existing state timings, reduced motion,
  transition priority/completion, stale completion tokens, overlay remount,
  and app-update fingerprint rejection.
- **LIKELY** — Keep the current external time controller advisory until a
  reviewed bridge exists. It should not use private IPC, UI automation, app
  restart, or active-atlas replacement as the final hot-switch design.
- **UNKNOWN** — Distribution, signing, notarization, and update survival require
  a separate Phase 1 decision before any modified Desktop build can be used as
  a durable installation.
