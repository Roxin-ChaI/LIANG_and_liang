# Phase 8C — Build 9922 runtime isolation recon

Scope: read-only inspection of the frozen official Build 9922 App. No Keychain
item, login credential, or production configuration value was read. No second
Codex process was started. Reproduce the non-secret evidence with
`python tools/inspect_runtime_isolation.py` in the Phase 8A trust context.

## Confirmed

- **CONFIRMED**: `/Applications/ChatGPT.app` still matches the frozen Build
  `9922` ASAR SHA256 `1f7939c1c781887c167043c4d1d307af3400d324685cfc315dfe2f80e634f483`.
  Bundle ID is `com.openai.codex`; official Team ID is `2DC432GLL2`.
- **CONFIRMED**: `.vite/build/bootstrap-DF0QwAxC.js` calls
  `app.setPath('userData', ...)` before the packaged-macOS
  `requestSingleInstanceLock()` branch. Its `pk` path function uses
  `CODEX_ELECTRON_USER_DATA_PATH` when present. The branch's
  `hasExplicitUserDataPath` flag also derives from that variable. A Chromium
  `--user-data-dir` argument alone is not the observed bootstrap override.
- **CONFIRMED**: the same bootstrap registers a `second-instance` handler
  after the lock branch. A failed lock exits the second process, so redirecting
  into an existing instance would be consequential.
- **CONFIRMED**: the packed runtime has separate main
  (`.vite/build/main-DUHZj4_w.js`) and preload (`.vite/build/preload.js`)
  chunks. Main contains BrowserWindow code and preload contains contextBridge
  code. Eight bundled Electron helper Apps are present for renderer, GPU,
  service and related roles.
- **CONFIRMED**: the official signed App has 14 XML entitlement keys, including
  `keychain-access-groups` values beginning with `2DC432GLL2.`. Those are
  declarations for the official Team-signed App, not proof of permissions for
  a locally ad-hoc-signed copy.
- **CONFIRMED**: the three inspected JS chunks contain no literal
  `keychain`, `safeStorage` or `keytar` reference. This narrow text search does
  not cover native modules, helpers, linked frameworks or indirect APIs.

## Not proven

- **NOT_PROVEN**: Electron's single-instance lock is isolated from the
  production instance solely by a different userData path. The source proves
  branch order, not the OS-level lock namespace or live helper behavior.
- **NOT_PROVEN**: userData, CODEX_HOME and temporary environment variables
  propagate to every helper and credential-using child process. Static bundle
  inspection cannot establish the absence of inherited GUI/login state.
- **NOT_PROVEN**: a locally ad-hoc-signed copy can read, or is denied access to,
  production Keychain entries. Keeping the same 14 entitlement keys does **not**
  retain Apple Developer Team identity. The actual Keychain outcome has not
  been tested and must not be inferred either way.
- **NOT_PROVEN**: any independent, authorized macOS GUI login session or VM is
  available for testing this App. A separate HOME within the current UID is
  not an independent login session.

## Unsafe boundary

- **UNSAFE**: launch a patched Codex under the production GUI user's session
  while Keychain separation and single-instance redirection remain unproven.
- **UNSAFE**: read production Keychain entries to investigate access, copy
  production credentials, or treat an ad-hoc signature's matching entitlement
  *names* as matching Apple Team authority.

The safe next path is an independently signed, project-owned Electron harness
for project-code behavior, followed by a real-App gate that requires a separate
authorized GUI user or VM with independently verified Keychain, userData,
socket and process isolation. Harness success is not patched-Codex success.
