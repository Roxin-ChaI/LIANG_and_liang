# Build 10789 minimal-entitlement launch test (Phase 8F)

Verdict: **MINIMAL_SIGNING_LAUNCH_FAILED**. The temporary App passed structural
signing and Electron integrity checks, but its only controlled launch exited
before Electron main initialization. This is not a live runtime or animation
PASS. No second signing/launch attempt was made after the rejection.

## Frozen source and entitlement plan

The source was the read-only, officially signed Build 10789 App mounted from
the [locally cached trusted DMG](current-codex-baseline-cache.md). The
component inventory includes 47 signed bundles, frameworks, executables,
native modules, and plugins. The offline Pet-only test plan removed all
OpenAI identity-bound claims: `com.apple.application-identifier` (3 component
claims), `com.apple.developer.team-identifier` (3),
`keychain-access-groups` (3), `com.apple.developer.aps-environment` (1), and
`com.apple.security.application-groups` (45). It also removed optional
app-sandbox (43), Apple Events automation (44), audio input (43), camera
(43), user-selected file access (43), network client (43), calendars (43),
and address book (1) claims. Counts refer to components, not distinct values.
The 3 embedded provisioning profiles were removed **only** from the test
copy; their contents were neither decoded nor reused. No replacement Team ID,
App ID, access group, or profile was fabricated.

The retained exception claims were `com.apple.security.cs.allow-jit` and
`com.apple.security.cs.allow-unsigned-executable-memory` on 16 process
components each, plus the source's existing
`com.apple.security.cs.disable-library-validation` on one process component.
Library/plugin signatures had empty effective entitlement dictionaries;
Electron process exceptions were not assigned to those code libraries.
The original per-component values can be reproduced read-only using
`tools/derive_test_entitlements.py --app <verified mount> --baseline
runtime-patch/builds/10789/trusted-baseline.json`. The plan had zero unknown
entitlement keys, but compatibility with AMFI remained unproven.

## Temporary signing and controlled launch

Only the fingerprint-gated temporary patched App was signed, inside-out, with
ad-hoc identity and Hardened Runtime. Before launch, all 47 actual component
entitlement dictionaries matched the plan; all 47 retained Hardened Runtime;
`codesign --verify --deep --strict` passed. The deterministic patched ASAR
SHA256 remained `236cf24c1916e811eea6e55e10591d404b76f8ac1e81974ebe7d845f687e68c0`;
its Electron integrity header matched the updated temporary Info.plist.
The main executable's `__TEXT,__text` SHA256 remained
`af99eb3609236b4047c386c62a75fff3d238f35ba0f0492a638aafd47daaac24`.
The full executable file hash changed as expected when its embedded code
signature was replaced; code bytes did not.

The temporary launch used separate `HOME`, `CODEX_HOME`, Electron userData,
`TMPDIR`, and socket paths. The already-running formal App was left alone.
The single allowed test process was PID 46709 and exited with code -6
(SIGABRT); no test Bridge socket appeared. Its dyld diagnostic identifies
`Codex Framework.framework` as the rejected mapped file and says the
non-platform framework and process have **different Team IDs**. This is a
runtime library-validation failure despite structurally valid signatures.
No login, Keychain authorization, or system-authorization prompt appeared;
no production Keychain item was read by these tools. Main, preload, renderer,
Bridge, Gu→Feng, Feng→Gu, overlay, and scheduler are all **NOT_TESTED**.

Apple documents
[Hardened Runtime library validation](https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.security.cs.disable-library-validation)
and its same-Team restriction. A narrowly scoped local signing variant might
need a different library-validation exception on the main process; this was
**not tested** after the rejection and is not a claim that the variant is
authorized, safe, or successful. The isolated Electron project harness PASS
does not substitute for a patched Codex launch PASS.
