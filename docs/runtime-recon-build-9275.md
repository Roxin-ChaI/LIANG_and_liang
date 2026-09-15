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
