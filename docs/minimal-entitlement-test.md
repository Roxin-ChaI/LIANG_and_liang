# Phase 8E: minimal-entitlement launch feasibility

## Source gate

The signing experiment requires an exact, trusted official Build 9922 App. The
frozen source is version `26.915.31945`, build `9922`, with `app.asar` SHA256
`1f7939c1c781887c167043c4d1d307af3400d324685cfc315dfe2f80e634f483`.
`tools/derive_test_entitlements.py` calls the existing trusted-source preflight
*before* inspecting components. No other build may be silently treated as
9922; a mismatched build produces an empty matrix and no signing plan.

On 2026-09-24, the installed official App was already Build **10789**, ASAR
SHA256 `c41157d36d701d3228c82e56852f49da2381941a7e5ccfac2d58b7e10e31aefd`.
The original official CDN URL now advertises a DMG of 650,455,829 bytes,
whereas the frozen checksum-verified Build 9922 DMG was 645,200,049 bytes.
No verified 9922 App/DMG remains in the checked local downloads, project,
cache, Trash, or temporary locations. The mutable URL is therefore **not** a
safe source for this experiment. No production App was copied or changed.

## Per-component policy (conditional on exact source)

The tool enumerates the main bundle, Frameworks, Helpers, XPC/appex containers,
and dylib/so code without traversing symlinks. It extracts each component's
own original signed entitlement key/value map, signer identifier/team,
Hardened Runtime flag and provisioning-profile presence. It does **not**
decode a profile or read Keychain entries. The result is a *proposal*, never
proof of launch authorization.

| Original signed claim | Proposed local-test treatment | Reason |
| --- | --- | --- |
| `keychain-access-groups` | Remove | Restricted; original OpenAI group cannot authorize an ad-hoc test signer. |
| `com.apple.developer.aps-environment` | Remove | Push capability requires matching profile; offline Pet test needs no push. |
| `com.apple.application-identifier` | Remove | Original App ID is bound to original signer/profile. |
| `com.apple.developer.team-identifier` | Remove | Do not assert OpenAI's team under another signature. |
| `com.apple.security.application-groups` | Remove | Even where the macOS entitlement class is unrestricted, the original group value is team-scoped. |
| Original per-component `com.apple.security.cs.allow-jit`, `allow-unsigned-executable-memory`, `disable-library-validation`, `allow-dyld-environment-variables` | Retain if original value is `true` | Electron/Hardened Runtime exceptions; never copy a claim to a component that did not originally have it. |
| Original non-Pet camera, microphone, calendar, Apple Events, user-selected file and network capabilities | Remove | Not required for a completely offline Pet startup experiment; may expose later feature failures. |
| Original `com.apple.security.app-sandbox=false` | Remove | False does not confer a sandbox capability. A `true` value blocks review. |
| Any other or malformed entitlement | Block | No inferred privilege or invented substitute value. |

The original **main App** key inventory (14 keys) is documented in
[`amfi-entitlement-diagnosis.md`](amfi-entitlement-diagnosis.md). The previous
read-only investigation observed 10 keys on the renderer Helper and 11 on the
service Helper, but did **not** archive their complete key/value maps or a
Framework-wide matrix. Consequently the required complete Build 9922
per-component entitlement difference is **NOT PROVEN** until an exact source
is available; no values from Build 10789 may fill those gaps.

## Signing/launch conditions

When an exact Build 9922 source is reacquired, first regenerate and review the
full matrix. A separate temporary-copy experiment must preserve Hardened
Runtime, sign nested code inside-out with each component's own proposed
entitlements, remove only the *temporary* copy's original provisioning
profile, and verify ASAR/bundle integrity and all signed values before a
single launch. A structural `codesign` PASS is not AMFI launch PASS. Any
Keychain/login/system authorization prompt requires stopping without approval.

This phase cannot proceed from the current Build 10789 source. Actual signing,
AMFI launch, main/preload/renderer, Bridge, animation, scheduler and visual
results are `NOT_TESTED`; the absence of an exact source is a `BLOCKED`
preflight, not a failed minimal-signing launch.

## Controlled-experiment preflight result

The read-only CLI was executed against `/Applications/ChatGPT.app` and returned
exit status `2` with:

```json
{"status":"BLOCKED_SOURCE_UNSUPPORTED_BUILD","sourceBuild":"10789","components":[]}
```

An independent subprocess test ran the same CLI on a synthetic newer-build
bundle with no `codesign`/`spctl` on `PATH`, and compared every fixture byte
before and after. It returned the same blocked result with zero writes. This
validates the source gate only; it does **not** validate signing or launch.
There was no temporary App, provisioning-profile operation, codesign call,
AMFI launch, production credential access or Keychain prompt. Commit 2 records
this blocked experiment honestly rather than claiming a signing failure.

## Primary references

- [Apple: Creating distribution-signed code for the Mac](https://developer.apple.com/documentation/xcode/creating-distribution-signed-code-for-the-mac/) — restricted entitlements need a matching profile; nested code should be signed inside-out, not with a blanket `--deep` sign.
- [Apple: App group containers](https://developer.apple.com/documentation/xcode/accessing-app-group-containers/) — Team ID binding of team-prefixed groups.
- [Apple: Hardened Runtime](https://developer.apple.com/documentation/security/hardened-runtime/) — runtime protection and controlled exceptions.
- [Apple: Resolving common notarization issues](https://developer.apple.com/documentation/security/resolving-common-notarization-issues/) — `--options=runtime` and signing verification context.
