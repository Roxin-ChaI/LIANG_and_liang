# Build 9275 Runtime Recon

Phase 3E is a read-only recon of the currently installed
`/Applications/ChatGPT.app`. It does not install a patch, sign the app, edit
the Pet, or preserve proprietary JavaScript in this repository. Findings in
this first stage are **CONFIRMED** by App metadata, an ASAR header walk, and
exact archived-resource SHA256 values. Internal call chains and patch sites
are deliberately left for the subsequent stage.

## Build Fingerprint

| Field | Confirmed value |
| --- | --- |
| Bundle ID | `com.openai.codex` |
| Version / Build | `26.908.70816` / `9275` |
| Executable | `/Applications/ChatGPT.app/Contents/MacOS/ChatGPT`, Mach-O arm64 |
| Executable SHA256 | `88175a62521bc57c1057b4d9d5ed350668a58c3ef59273eace7069faa21c442f` |
| Electron | `42.3.0` in archived `package.json` devDependencies |
| Chromium/framework version | `152.0.7977.83` in Codex Framework `Info.plist` |
| `app.asar` SHA256 | `100b3a06768326eec58ae32e54fa7b85368fef8d4ead5a5866ecb0e8751bdeaa` |
| Code signature | Embedded arm64 signature and stapled ticket reported by `codesign -dv`; **strict verification fails** with `invalid signature (code or signature have been modified)` |

The invalid-signature diagnostic is a pre-existing read-only observation in
this phase; it is not repaired or treated as successful verification.

## Bundle Layout

`Contents/Resources/app.asar` is the Electron application archive. Its current
ASAR header is 2,515,888 bytes and enumerates 9,144 entries. The preload is
`.vite/build/preload.js`; the current main custom-avatar candidate is
`.vite/build/main-DaMR-wdT.js`. The renderer lives in `webview/assets/`.

## Packaging

The ASAR has 8,743 packed and 401 unpacked entries, including 7,415 `.js`
entries. The inspected Pet-related renderer chunks are bundled/minified JS.
There are no `.map` entries in the archive. No extracted code or source maps
are committed.

## Runtime Chunk Candidates

| Role candidate | Archived path | SHA256 | Confirmed cue |
| --- | --- | --- | --- |
| Preload | `.vite/build/preload.js` | `9dba229e0b3cfa1cc9a7e78925b5f168b7f7385e1c18d785d13ce8e823e65207` | Archive path |
| Main custom-avatar service | `.vite/build/main-DaMR-wdT.js` | `0765260be74e8843630d5a92e30bca574783892688e67180c119a5c58679bb61` | `customAvatars`, `spriteVersionNumber`, `spritesheetDataUrl` |
| Core renderer | `webview/assets/app-initial-4d7ea7f81c2d.js` | `5dcf4a29db25b086f9bd11d053eec60cf0c50bfd988494969cec452e03f19245` | Unique `data-codex-pet-id`, `data-codex-pet-state`, out-of-range warning |
| Overlay | `webview/assets/avatar-overlay-native-page-efa96d74af15.js` | `51c369ad2dc365550b463e3cb119da97d94c2ffc98e01a9f18b53287d920f0cf` | `first-awake-pet-notification-avatar-ids`, `spriteVersionNumber` |
| Mascot/wrapper | `webview/assets/avatar-mascot-button-7a295935c1d3.js` | `adb931faef70d16b02e9099e973563ae5a5d38a2c316770e22d116de876919fb` | `waving`, `jumping` |
| Pets Settings | `webview/assets/pets-settings-route-c49fd75fc38f.js` | `b5a75703f92baa93703edf965ef3b2e141467934c8a67770bc69b2d873e47c55` | Route path |

The main candidate filename and SHA happen to match the old recorded chunk;
that is a measured equality, not a licence to reuse Build 8881 renderer
symbols or patch offsets.

## Search Anchors

The archive scan covered packed `.js` in `.vite/build/` and
`webview/assets/`. These current-build observations identify candidates but
are not yet patch locators:

| Anchor | Confirmed occurrence scope |
| --- | --- |
| `custom-avatars`, `cloud-pets`, `data-codex-pet-id`, `data-codex-pet-state`, out-of-range warning | Core renderer chunk |
| `customAvatars`, `spritesheetDataUrl` | Main service and core, plus supporting modules |
| `selected-avatar-id` | Main support chunks and `webview/assets/src-996ff3571e1f.js` |
| `first-awake-pet-notification-avatar-ids` | Overlay chunk |
| `waving`, `jumping` | Core, mascot/wrapper, and selected supporting chunks |
| `spriteVersionNumber`, `spritesheetUrl`, `spritesheetPath` | Multiple loader/model/settings chunks; require structural disambiguation |

The numeric strings `1536` and `2288` occur widely and are never used alone
as Pet anchors. Generic state words `waiting`, `running`, `review`, `failed`
also have many non-Pet occurrences.

## Current Pet Call Chains

The following are **CONFIRMED** in the current archived chunks, not inferred
from the old hashed renderer names.

### Selected custom Pet loading

```text
selected-avatar-id (renderer setting)
  → overlay selected-avatar hook (`kd`-shaped custom: branch)
  → core by-ID key ["custom-avatars", "by-id", id]
  → renderer service customAvatars.loadAvatar(id)
  → main service delegation
  → `.vite/build/src-CCXHtyvY.js` Pet metadata loader
  → pet.json + bounded relative spritesheetPath + image bytes
  → v1/v2 dimensions check + base64 data URL
  → core avatar option → source converter → overlay mascot
  → mascot wrapper → core background-image renderer
```

The main service wrapper for `loadAvatar` has one structural instance and
delegates to the currently archived loader. That loader reads `pet.json`,
parses the native manifest, checks the spritesheet's type and exact
`1536×1872` (v1) or `1536×2288` (v2) dimensions, then returns
`spritesheetDataUrl`. The source converter yields the native
`{petId,spriteRowCount,spritesheetUrl}` shape; the core visual sets the CSS
background image. Native `pet.json` and the one-Pet-ID contract are intact.

### Settings > Pets > Refresh

The current Pets Settings route's `settings.pets.refresh` control invokes
`onRefreshCustomAvatars`, whose handler invalidates three exported query
prefixes: `['custom-avatars']`, `['cloud-pets','list']`, and
`['cloud-pets','selection']`. Prefix invalidation includes the active local
custom by-ID query. The current by-ID query has infinite stale time, no
window-focus refetch, no retry, and `gcTime:0`, so merely changing a file on
disk does not change the renderer data URL. The active refetch crosses the
existing renderer→main service IPC, re-reads the manifest/spritesheet, and
delivers a fresh `spritesheetDataUrl`; overlay source recomputation is the
point where the new atlas takes effect. **CONFIRMED**: this is query-driven,
not a renderer-owned direct filesystem reread. **UNKNOWN**: unrelated
filesystem observers outside the inspected Pet chain.

### Animation and interaction

The v2 table remains 1536×2288, 8×11 at 192×208, with frame counts
`[6,8,8,4,5,8,6,6,6,8,8]`. The nine named states are **CONFIRMED** in the
current core frame descriptor:

| State | Row | Frames | One pass (ms) |
| --- | ---: | ---: | ---: |
| idle | 0 | 6 | 1100; slow idle 6600 |
| running-right | 1 | 8 | 1060 |
| running-left | 2 | 8 | 1060 |
| waving | 3 | 4 | 700 |
| jumping | 4 | 5 | 840 |
| failed | 5 | 8 | 1220 |
| waiting | 6 | 6 | 1010 |
| running | 7 | 6 | 820 |
| review | 8 | 6 | 1030 |

Idle loops. Each non-idle named row plays three times and then loops the
six-times-slow idle descriptor; this does not mean its notification has
ceased. Reduced motion holds the first frame. The core timer uses CSS
background-position and clears its timeout on renderer dependency changes.
V2 look angles remain 16 directions at 22.5°: 0–7 row 9, 8–15 row 10.

The mascot wrapper's pointer-enter/leave state switches `jumping` and back
to the underlying state. Overlay drag supplies `running-right` or
`running-left` after ±4 screen-pixel horizontal movement and clears that
transient on release/cancel. The overlay's first-awake notification maps to
`waving` and expires after eight seconds; it is remembered per avatar ID.
Loading notification maps to `running`; warning to `waiting`; danger to
`failed`; success to `review`; info/no notification to `idle`.

## Renderer Hierarchy and Clipping

The current overlay owner builds the mascot using one `source` converter
call and hands the visual to the mascot-button chunk. The inspected chain is:

```text
overlay selected avatar → overlay frame owner
  → absolute draggable mascot box (position/width/height, pointer handlers)
  → data-avatar-overlay-hit-region="mascot" (h-full w-full)
  → relative size-full presentation wrapper
  → pet fade container (absolute inset-0)
  → mascot button (pointer enter/leave)
  → core 192×208 background-image visual
```

The root `<main>` of the overlay frame has `relative h-screen w-screen`
and `overflow-hidden`; it encloses the normal mascot subtree. This is a
**CONFIRMED DOM clipping obstacle** for an oversized sibling inside the
existing Pet fade container. The normal drag hitbox is the absolute mascot
box and marked hit-region; expanding either would change interaction.

The layout wrapper immediately above that root returns the root component
as its only child. A transition-only visual sibling at that wrapper level,
*outside* the clipping `<main>`, is a **LIKELY clipping-safe structural
candidate** without permanently changing Desktop overlay overflow or the
mascot drag box. It must be absolute, pointer-events:none, and use the frozen
canvas offsets. The native overlay window/viewport still inherently crops
pixels beyond the physical window edge; Phase 3D visual QA must test edge
placements before claiming full presentation safety.

## Build 8881 → 9275 Delta

| Area | Classification | Measured observation |
| --- | --- | --- |
| Main custom-avatar wrapper | UNCHANGED_SEMANTICS | Archived filename and SHA are equal; current service delegation has one match. |
| Custom loader | CHANGED_STRUCTURE | Current loader/support chunk is `.vite/build/src-CCXHtyvY.js`; native manifest/atlas validation semantics remain. |
| Core, overlay, mascot, Pets Settings | CHANGED_STRUCTURE | Current filenames and SHA256 values differ from Build 8881 records; old hashed names are absent. |
| Local/cloud Pet query keys | UNCHANGED_SEMANTICS | Same three Refresh prefixes and `custom` by-ID key/policy were found. |
| Nine-state table/timing and 16 look rows | UNCHANGED_SEMANTICS | Current literals and completion branch match the documented runtime semantics. |
| Renderer hierarchy/clipping | UNKNOWN delta | Current main root clip and wrapper chain are confirmed; prior document did not establish an equivalent clipping-safe sibling boundary. |
| Preload/main IPC | UNKNOWN delta | Current preload still exposes contextBridge/IPC; prior exact preload hash and channel-layout comparison were not established. |

Minified symbol identities are current-build observations only. No old symbol
is used as a locator unless the current structural context is revalidated.

## Build 9275 Patch-Point Candidates

Every candidate below is subject to the Build 9275 fingerprint gate and
composite-anchor exact-one locator test. This is **not** authorization to
patch the real app.

| Point | Current chunk | Structural anchor / matching strategy | Confidence and reason |
| --- | --- | --- | --- |
| A. Dual-form load | `.vite/build/main-DaMR-wdT.js`, delegated loader `.vite/build/src-CCXHtyvY.js` | `customAvatars` service registration + one `loadAvatar` delegation + native `spritesheetDataUrl`; loader has `pet.json`/`spritesheetPath`/v2 dimension validation | LIKELY: retain native result and attach two separately validated form URLs once. |
| B. Hot source switch | `webview/assets/avatar-overlay-native-page-efa96d74af15.js` | selected custom hook + native source converter import + unique `source:Kr(c)` call within mascot creation | LIKELY: choose one already-loaded atlas URL before normal mascot; leave Pet ID/state rows unchanged. |
| C. One-shot descriptor | `webview/assets/app-initial-4d7ea7f81c2d.js` | v1/v2 layout + complete nine-state row map + out-of-range warning adjacent to descriptor generator | LIKELY: keep the native map and add a separate trusted arbitrary-frame descriptor, not another named state. |
| D. Completion/timing | same core chunk | `loopStartIndex` descriptor + frame-timeout effect + Pet data attributes | LIKELY: a tokened one-shot completion hook belongs at final timer boundary, without changing native finite/idle behavior. |
| E. Transition owner | overlay chunk | selected-avatar hook → keyed owner component → mascot state/source props | LIKELY: overlay owner can prioritize transition over drag/hover/task, preserving latest underlying state. |
| F. Oversized sibling | overlay chunk | layout wrapper's sole root-component render, plus mascot marked hit-region and normal `source` call | LIKELY: add transition-only absolute sibling outside normal draggable box. |
| G. Clipping-safe boundary | overlay chunk | root `relative h-screen w-screen overflow-hidden` + `data-avatar-overlay-content-frame` + layout wrapper just outside root | LIKELY: wrapper-level sibling avoids DOM root clipping; requires viewport-edge review. |
| H. Form commit | overlay chunk | selected-avatar owner + source-converter/mascot creation dependency group | LIKELY: commit `{form,source,playbackEpoch}` together after tokened completion, then remove transition sibling. |
| Local control bridge | `.vite/build/preload.js` and main service chunk | existing typed `contextBridge` renderer→main invoke + registered custom-avatar service | LIKELY: a dedicated validated command/event could be added in a later threat-modelled phase; private `ipc.sock` is excluded. |

## Locator Dry Run

`runtime-patch/prototype/build-9275-locator.mjs` gates on the installed
Build 9275 version, build number, ASAR SHA256, and the seven archived Pet
chunk SHA256 values before searching. It extracts current packed chunks in
memory, then searches each patch site by a full local shape plus nearby
Pet-specific structural anchors. The eight matches below were each unique
in the current Build 9275 archive. These are **CONFIRMED locator results**,
not a running-app transition test.

| Patch locator | Matches | Context SHA256 |
| --- | ---: | --- |
| Dual-form custom-avatar result | 1 | `504f1f1ca34fd3954132ecb76aec681799b964324e13e7e18d55460ba6a2b87a` |
| Hot source switch | 1 | `9ce747a5b0835eaebf5f69d417ff83d9e07376efe34897b045be8c9db26651a3` |
| One-shot frame descriptor | 1 | `a743b8aa0c40a2a3b515d476cef6b6e2032b9bafcacd92be39330e2dcb7a22af` |
| Completion/timing | 1 | `c0c52f001cc7822e9c3618ec0268398d0ceb34f2ddd60c17c4f9e837cb07329b` |
| Transition owner | 1 | `aefa4fd3c2076837a9a84cbe425719846510910551b875cce9cb613f66b81c3b` |
| Atomic form-commit owner | 1 | `3c5f74b001f701c324cb0ef0c19b2e7ffd567886fd3e3455405f789326370029` |
| Oversized transition sibling | 1 | `75d612631bc47f8eb5f89ec9ffe6135b86f4f8514119020049bb5aa81447d75a` |
| Clipping-safe structural boundary | 1 | `ed2c5d7bccb5c5d6918e6fbcfc029f441061f31f106a963545c9ec26d20907cb` |

## Clipping Recon

**CONFIRMED:** the normal mascot's absolute box and
`data-avatar-overlay-hit-region="mascot"` each have one structural match and
remain inside the clipped overlay `<main>`. That `<main>` uses
`overflow-hidden`. The layout wrapper's one render of the clipped root is
outside the root component. A transition-only sibling at that wrapper
render site therefore does not inherit the root's DOM clipping and can
preserve the normal mascot hitbox. The dry-run labels this structural site
`CLIPPING_SAFE_INSERTION_FOUND`. **LIKELY**, not proven by a live renderer:
an absolute, pointer-events-none sibling there will display the oversized
transition within the overlay viewport. Native window-edge cropping remains
**UNKNOWN** until Phase 3D visual testing.

## Temporary Patch, Original Integrity, and Cleanup

The locator created one OS temporary directory, copied the current chunks
there, inserted a comment marker exactly once immediately before the layout
wrapper's normal root render in a temporary overlay copy, and ran
`node --check` on that temporary file. Syntax was **PASS**. Removing the
marker restored the original bytes exactly, proving the normal branch was
not changed by the dry-run. The installed ASAR SHA256, size, mode, mtime,
version/build, and archived key chunk hashes matched their pre-run values
afterward. No real App, `.asar`, chunk, signature, or Codex configuration was
modified. The exact temporary directory was removed; cleanup was **PASS**.
The installed App's read-only `codesign --verify --deep --strict` result is
an invalid-signature warning, unchanged from the recon. No signing action
was taken.

## Phase 3D Retry Readiness

**READY_TO_RETRY_PHASE_3D_RUNTIME_POC** applies to the Build 9275
fingerprint-gated locator and temporary-copy syntax/structure only. The
Phase 3D runtime PoC must still verify live one-shot completion, native
form commit, hit-region preservation, and oversized-frame viewport edges.
No app patch is installed by Phase 3E, and the signature warning must be
handled explicitly before any future signed-app deployment plan.
