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
