# Phase 8B isolated runtime test — pre-launch gate

Verdict: `RUNTIME_ISOLATION_BLOCKED`. No temporary Electron App was launched.
This is a pre-launch safety result, not a real-runtime PASS.

## Read-only source trust evidence

The Phase 8A verified execution context (outside the restricted command sandbox)
successfully checked `/Applications/ChatGPT.app`:

- Version `26.915.31945`, Build `9922`, Bundle ID `com.openai.codex`.
- Original `app.asar` SHA256:
  `1f7939c1c781887c167043c4d1d307af3400d324685cfc315dfe2f80e634f483`.
- Electron raw ASAR header and Info.plist integrity:
  `a2c8179f53b4722a1d847ccd1753ad60fae8a84a08caf3b40f360edeac6a0a9a`.
- Executable SHA256:
  `dfe5654498e939d355702fa66e6e2400e55ec0ade61048e19e264f4bdc70b847`.
- `codesign --verify --deep --strict --verbose=4`: PASS.
- Team ID `2DC432GLL2`, hardened runtime: PASS.
- Entitlements parse as XML; 14 keys; application/team identifiers and the two
  expected keychain access groups match: PASS.
- `spctl --assess --type execute --verbose=4`: accepted, Notarized Developer ID.

Within the restricted command sandbox, the same strict signature check also
fails for the unmodified system Calculator App. The harness now reports
`TRUST_CONTEXT_UNAVAILABLE` there; it never substitutes hashes for a valid
SecTrust result. The official source preflight passes only in the Phase 8A
verified execution context.

## Isolation audit

Build 9922's packed bootstrap explicitly sets Electron `userData` from
`CODEX_ELECTRON_USER_DATA_PATH` when present. A Chromium
`--user-data-dir=...` argument alone does not establish that bootstrap path.
The harness now supplies and verifies both values. The same bootstrap calls
`requestSingleInstanceLock()` for packaged macOS builds when that explicit
userData override is present, but static inspection alone does not prove the
lock cannot redirect to a production instance.

The official App entitlements contain production
`keychain-access-groups = ["2DC432GLL2.*", "2DC432GLL2.com.openai.shared"]`.
Changing HOME, CODEX_HOME, Electron userData, TMPDIR and bridge socket does
not isolate macOS Keychain. Ad-hoc re-signing a temporary App is not by itself
proof that the process cannot read production credentials. No independent
Keychain-denial or identity-isolation mechanism has been verified. Therefore
the launch gate remains closed (`identityAndKeychainIsolationProven=false`,
`launchAllowed=false`).

No App copy, patch, ad-hoc signing, bridge call, scheduler E2E, renderer
observation, window screenshot or visual runtime QA was attempted after this
blocker. The formal App and real `~/.codex` were not written. No runtime PASS
should be inferred from static tests or the trusted-source preflight.

The full repository regression passed in the verified local context:
`210 passed, 12 subtests passed`. The same suite inside the restricted sandbox
had 18 Unix-socket permission failures unrelated to the application logic.
