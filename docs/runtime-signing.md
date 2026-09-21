# Runtime patch signing analysis

## Phase 7 scope

Signing experiments are permitted only on a system-temporary copy of `ChatGPT.app`. The real `/Applications/ChatGPT.app` is read-only, no Developer ID or Apple account is used, no notarization is attempted, and no keychain signing identity is accessed.

## Current baseline observation

The Phase 7 recipe is frozen for version `26.908.70816`, build `9275`, with `app.asar` SHA256 `100b3a06768326eec58ae32e54fa7b85368fef8d4ead5a5866ecb0e8751bdeaa`.

At Phase 7 execution time, the installed application had already updated:

- version: `26.915.31945`
- build: `9922`
- `app.asar` SHA256: `1f7939c1c781887c167043c4d1d307af3400d324685cfc315dfe2f80e634f483`
- architecture: arm64
- bundle identifier: `com.openai.codex`
- Team ID reported by the embedded signature: `2DC432GLL2`
- hardened-runtime flag: present
- notarization ticket: reported as stapled

The read-only baseline command `codesign --verify --deep --strict` returned `invalid signature (code or signature have been modified)`. Entitlement extraction also reported an invalid entitlements blob and warned that the OS would ignore it. No valid entitlement plist could therefore be preserved.

## Patch impact and ad-hoc strategy

Replacing `Contents/Resources/app.asar` changes a sealed resource and invalidates the existing bundle signature. Content restore can restore the exact ASAR hash, but it cannot reconstruct signature metadata after a re-sign operation.

The intended temporary-copy strategy is:

1. Record executable hash, ASAR hash, bundle ID, signature details, Team ID, hardened-runtime status, and entitlements.
2. Patch only the temporary copy through the fingerprint-gated installer.
3. Confirm the executable and bundle ID are unchanged and the patched signature is invalid as expected.
4. If and only if a valid baseline entitlement plist is available, ad-hoc sign the temporary copy with `codesign --force --deep --sign - --entitlements <preserved.plist>` and run strict verification.
5. Restore ASAR content and report signature restoration separately.

Because the current app no longer matches Build 9275, the smoke tool stopped before creating or patching a temporary copy. Because the current signature exposes no valid entitlement plist, blindly ad-hoc signing would risk removing required capabilities. The Phase 7 result is therefore:

- patched-but-signature-invalid state: `NOT_TESTED_BUILD_MISMATCH`
- ad-hoc signing: `NOT_TESTED_BUILD_MISMATCH`
- entitlement preservation: `BLOCKED_BASELINE_ENTITLEMENTS_INVALID`
- production strategy: `SIGNING_STRATEGY_PENDING`

## Auto-update and production risks

An application update changes version, build, ASAR hash, chunk names, chunk hashes, and often minified locator shapes. The installer must refuse the old recipe rather than fuzzy-patching a new build. A production flow needs a new audited spec for each supported build, an explicit user authorization gate for the real App, a safe entitlement/signing solution, and a defined interaction with automatic updates.

Phase 7 does not modify or launch the real App, start a second Codex instance, sign with a private identity, or claim that ASAR content restore is signature restore.
