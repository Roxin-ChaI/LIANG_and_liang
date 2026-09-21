# Current Codex Pet runtime recon (Build 9922)

## Scope and evidence

This Phase 7A recon is a read-only examination of
`/Applications/ChatGPT.app`. It did not edit, sign, quarantine, launch,
replace, or otherwise mutate the installed application. The findings below
come from bundle metadata, Mach-O inspection, SHA256 measurements, and an
ASAR header walk/extraction into a system-temporary directory. No extracted
or patched proprietary JavaScript is stored in this repository.

Confidence labels mean:

- **CONFIRMED**: directly observed in the current bundle or uniquely matched
  in the current archived runtime.
- **LIKELY**: the structural site and surrounding semantics are confirmed,
  but the proposed injected behavior has not run inside Codex Desktop.
- **UNKNOWN**: the available read-only evidence does not establish the fact.

## Current build fingerprint

| Field | Current value | Confidence |
| --- | --- | --- |
| Bundle identifier | `com.openai.codex` | CONFIRMED |
| Version | `26.915.31945` | CONFIRMED |
| Build | `9922` | CONFIRMED |
| Architecture | Mach-O 64-bit `arm64` | CONFIRMED |
| Electron version | `42.3.0` from archived `package.json` | CONFIRMED |
| Chromium/framework version | `153.0.8010.48` from Codex Framework `Info.plist` | CONFIRMED |
| Executable SHA256 | `dfe5654498e939d355702fa66e6e2400e55ec0ade61048e19e264f4bdc70b847` | CONFIRMED |
| `app.asar` SHA256 | `1f7939c1c781887c167043c4d1d307af3400d324685cfc315dfe2f80e634f483` | CONFIRMED |

## Packaging and runtime locations

`Contents/Resources/app.asar` is the application archive. Its current header
walk found 15,023 packed entries and 402 unpacked entries. Pet code is bundled
and minified JavaScript. The archive contains source-map comments, but no
`.map` entries, so source maps are unavailable in the installed bundle.

| Role | Current archived path | SHA256 | Confidence |
| --- | --- | --- | --- |
| Main runtime | `.vite/build/main-DUHZj4_w.js` | `9e8a3bd79c817064f28693ca26aa1378895e07ab2108c78c42d0ea20dac9d66e` | CONFIRMED |
| Preload | `.vite/build/preload.js` | `cbb4eafff381b835dc9c371c1d9d3c455ab95c1641d955bd975e03e2a88fb2ea` | CONFIRMED |
| Native custom-avatar loader | `.vite/build/src-C3YaUE83.js` | `14c8c23e8b8dfa874d3fb5a50d54fb28eccf55fb83232c3ab29cb7c0ef0a0472` | CONFIRMED |
| Core Pet renderer | `webview/assets/app-initial-a498f911edeb.js` | `34a75db63c7137eb4caecdba1f36d631c10c7912487e532fd5e9dafb175bb9be` | CONFIRMED |
| Native avatar overlay | `webview/assets/avatar-overlay-native-page-34cd5ae3858a.js` | `350a0e48425ea6e71636842a2f680d54e39acefeb70760fa8702fa8a8be8955f` | CONFIRMED |
| Mascot wrapper | `webview/assets/avatar-mascot-button-171f2736a391.js` | `826f2fdde13849f68f977d972c78ebe992fdd4a8cebce622e806277172f505c8` | CONFIRMED |
| Pets Settings route | `webview/assets/pets-settings-route-8ba274e79a29.js` | `27884ebe48384c142cfeb04576abcae636da208987aaf1172919897d28137ef0` | CONFIRMED |

## Search-anchor results

The following Pet-specific anchors were found in the current runtime:

- Core: `custom-avatars`, `cloud-pets`, `data-codex-pet-id`,
  `data-codex-pet-state`, `Codex pet animation frame is out of range`,
  `spritesheetUrl`, and the complete v1/v2 geometry/state tables.
- Main/native loader: `customAvatars`, `pet.json`, `spriteVersionNumber`,
  `spritesheetPath`, `spritesheetDataUrl`, `1536`, and `2288`.
- Overlay: `first-awake-pet-notification-avatar-ids`, selected-avatar
  resolution, mascot task state, source conversion, drag geometry, and the
  clipped root/outer layout-wrapper pair.
- Mascot: `waving`, `jumping`, hover enter/leave, source, transient state,
  and the core Pet renderer call.
- Settings: the Pets Refresh control and `onRefreshCustomAvatars` prop chain.

Generic strings such as `running`, `waiting`, `review`, `failed`, `1536`, and
`2288` have many unrelated matches and are not used alone as locators.

## Custom Pet load chain

The current chain is **CONFIRMED**:

```text
selected-avatar-id
  -> overlay selected-avatar hook
  -> local custom by-ID query ["custom-avatars", "by-id", id]
  -> renderer customAvatars.loadAvatar(id)
  -> main service loadAvatar delegation
  -> native loader in .vite/build/src-C3YaUE83.js
  -> bounded pet directory + pet.json parse
  -> bounded spritesheetPath resolution
  -> PNG/WebP dimension validation
  -> spritesheetDataUrl + spriteVersionNumber
  -> core source conversion to spritesheetUrl/spriteRowCount
  -> overlay mascot wrapper
  -> core CSS background-image renderer
```

The native loader still accepts `spriteVersionNumber` 1 or 2, requires width
1536, requires height 1872 for v1 or 2288 for v2, and returns a base64 data
URL. Relative path resolution rejects directory escape. Native failure is
still represented by a null result, which is the fallback behavior the Liang
loader extension must preserve.

## Settings > Pets > Refresh chain

The current chain is **CONFIRMED**:

```text
Pets Settings Refresh button
  -> onRefreshCustomAvatars
  -> query/cache invalidation for custom-avatars,
     cloud-pets/list, and cloud-pets/selection
  -> active local custom by-ID refetch
  -> existing renderer-to-main service call
  -> native pet.json/spritesheet reread
  -> fresh spritesheetDataUrl
  -> selected-avatar/source recomputation
  -> overlay/core renderer receives the new atlas URL
```

The local custom list has infinite stale time and the by-ID query has
`gcTime: 0`, infinite stale time, no window-focus refetch, and no retry.
Consequently an on-disk atlas replacement does not become visible until the
query is explicitly invalidated/refetched. The atlas becomes effective when
the newly loaded avatar object is converted into the overlay's core Pet
source. There is no evidence in this chain of a direct renderer filesystem
watcher.

## Animation state machine

The state machine remains in the core Pet renderer. The v2 atlas contract is
1536x2288, 8 columns by 11 rows, 192x208 cells, with required frame counts
`[6,8,8,4,5,8,6,6,6,8,8]`.

| State | Row | Frames | Native timing |
| --- | ---: | ---: | --- |
| `idle` | 0 | 6 | 1100 ms; slow idle 6600 ms |
| `running-right` | 1 | 8 | 1060 ms |
| `running-left` | 2 | 8 | 1060 ms |
| `waving` | 3 | 4 | 700 ms |
| `jumping` | 4 | 5 | 840 ms |
| `failed` | 5 | 8 | 1220 ms |
| `waiting` | 6 | 6 | 1010 ms |
| `running` | 7 | 6 | 820 ms |
| `review` | 8 | 6 | 1030 ms |

Idle loops. Every named non-idle row is repeated three times, then enters the
six-times-slower idle descriptor. Reduced motion holds the first frame. The
timer writes CSS background position and clears its timeout when dependencies
change. The v2 look directions remain 16 angles at 22.5-degree increments:
indexes 0-7 use row 9 and indexes 8-15 use row 10.

The mascot wrapper still maps pointer hover to transient `jumping`. Overlay
drag still selects `running-right` or `running-left`. First-awake greeting
maps to `waving`; loading maps to `running`; warning maps to `waiting`;
danger maps to `failed`; success maps to `review`; and info/no notification
maps to `idle`.

## Overlay, mascot, preload, and main ownership

- **CONFIRMED:** the overlay chunk owns selected-avatar resolution, task-state
  mapping, drag/hover composition, normal source conversion, and frame layout.
- **CONFIRMED:** the mascot wrapper owns hover transient selection and calls
  the core Pet renderer without changing atlas geometry.
- **CONFIRMED:** the normal mascot remains inside a marked fixed drag hitbox.
- **CONFIRMED:** the root `<main>` retains `overflow-hidden`.
- **CONFIRMED:** the layout component immediately outside the root renders the
  root component from `frameProps` plus `layout`; this is the only current
  outer sibling insertion boundary found for an oversized transition.
- **CONFIRMED:** preload exposes the existing `electronBridge` through
  `contextBridge` and has an exact-one exposure site.
- **CONFIRMED:** main owns the avatar overlay manager and exposes its visible
  `webContents`; the manager construction/registration site is unique.

The outer sibling is a **LIKELY** clipping-safe DOM insertion point. Native
overlay-window edge clipping remains **UNKNOWN** until an authorized live
temporary-copy test.

## Build 9922 Liang patch points

All counts below are against the exact current chunk fingerprints above. The
anchors are structural descriptions, not offsets or inherited minified
symbol names. Each exact recipe needle is local to its recorded current
chunk and has one match.

| # | Required patch point | Current chunk | Structural anchor | Count | Confidence |
| ---: | --- | --- | --- | ---: | --- |
| 1 | dual-form loader/model | main | unique custom-avatar `loadAvatar` delegation carrying execution host, avatar ID, and WSL preference | 1 | LIKELY |
| 2 | source hot switch | overlay | unique normal mascot `source` converter call beside selected avatar, look frame, state, and size | 1 | LIKELY |
| 3 | transition descriptor | core | unique named-state descriptor entry immediately after the v1/v2 atlas table | 1 | LIKELY |
| 4 | transition completion | core | unique finite-animation terminal branch immediately before background-position advance | 1 | LIKELY |
| 5 | operation-token guard / transition owner | overlay | unique outer layout component receiving `frameProps`, runtime layout, and root component | 1 | LIKELY |
| 6 | form commit | overlay | unique normal mascot source/state/style construction whose source changes only after committed form/epoch changes | 1 | LIKELY |
| 7 | oversized transition sibling | overlay | unique outer layout component that owns the clipped root result | 1 | LIKELY |
| 8 | clipping-safe insertion | overlay | unique memoized outer layout render of the clipped root; the root clip itself is also unique | 1 | LIKELY |
| 9 | Local Bridge main service | main | unique avatar overlay manager construction followed by hotkey controller registration | 1 | LIKELY |
| 10 | preload typed event | preload | unique `electronBridge` context exposure followed by the window message listener | 1 | LIKELY |
| 11 | overlay event subscription | overlay | unique selected-avatar owner entry receiving `selectedAvatar` and `selectedAvatarId` props | 1 | LIKELY |
| 12 | `requestTargetForm` binding | overlay | unique full-screen transparent root class/initialization boundary adjacent to the selected-avatar owner | 1 | LIKELY |

The deployable recipe also needs exact-one subordinate locators for native
underlying-state tracking and normal-visual suppression; the current
`mascotState` property and width/height style construction each have one
match. The recipe keeps the native atlas source, state table, hitbox, root
clip, and source-converter fallback present. A count of one proves a
deterministic injection site, not live runtime correctness.

## Build 9275 -> current delta

| Area | Classification | Current finding |
| --- | --- | --- |
| Custom Pet load semantics | UNCHANGED_SEMANTICS | `pet.json`, bounded `spritesheetPath`, v1/v2 dimension validation, data URL result, and native null fallback remain. |
| Refresh semantics | UNCHANGED_SEMANTICS | The same local/cloud query families are invalidated and the active by-ID loader is refetched. |
| v2 geometry and nine states | UNCHANGED_SEMANTICS | Dimensions, row counts, named state mapping, three-pass finite behavior, slow idle tail, and 16 look directions remain. |
| Overlay ownership/hitbox | UNCHANGED_SEMANTICS | Selected avatar, source, task state, drag hitbox, clipped root, and outer layout wrapper remain. |
| Main/preload bridge layers | UNCHANGED_SEMANTICS | Visible overlay `webContents`, context isolation, IPC renderer, and contextBridge exposure remain available. |
| Hashed chunks | CHANGED_STRUCTURE | Main, loader, core, overlay, mascot, and Settings filenames/hashes differ from Build 9275. |
| Minified symbols and exact needles | CHANGED_STRUCTURE | Every frozen 9275 locator needle has zero matches in Build 9922; all current locators were independently rebuilt. |
| Transition runtime hooks | CHANGED_STRUCTURE | Equivalent descriptor, completion, owner, source, outer-sibling, and normal-visual sites exist under new local shapes. |
| Required Phase 7 operation semantics | UNCHANGED_SEMANTICS | All 12 required operations have a current exact-one structural site. |
| Live oversized viewport behavior | UNKNOWN | DOM boundary is present; native window-edge behavior still needs a separately authorized temporary-copy run. |

No required patch operation is removed. The current architecture is therefore
compatible with recipe migration, subject to recipe tests, temporary-ASAR
syntax/static verification, and the separate baseline signing diagnosis.

## Recon conclusion

- Current build frozen: **CONFIRMED** (`26.915.31945` / `9922`).
- Current `app.asar` frozen: **CONFIRMED**
  (`1f7939c1c781887c167043c4d1d307af3400d324685cfc315dfe2f80e634f483`).
- Twelve current structural locators: **CONFIRMED**, each count 1.
- Build 9275 recipe reuse without migration: **BLOCKED**; every old exact
  needle is absent and the fingerprint gate correctly rejects Build 9922.
- Build 9922 recipe migration: **READY** from runtime architecture evidence.
