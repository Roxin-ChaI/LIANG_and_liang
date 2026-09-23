# Phase 8D: AMFI entitlement diagnosis (Build 9922)

## Evidence and limits

The Phase 8C temporary patched App passed `codesign --verify --deep --strict`
after an ad-hoc re-sign, but never entered `main`. A read-only query of the
17:20:12–17:20:17 local `amfid` window identifies the rejected component as
`ChatGPT.app/Contents/MacOS/ChatGPT`. It reports both:

- `Code=-427`: unable to retrieve certificate chain;
- `Code=-424`: ad-hoc signed app with restricted entitlements.

It **does not** print an `Unsatisfied Entitlements: <key>` line. Thus the
failure class is `ENTITLEMENT_AUTHORIZATION_FAILED`, while the exact key or
combination that AMFI evaluated first is **not confirmed**. `codesign` PASS is
only `SIGNATURE_STRUCTURE_VALID`, not process-launch authorization. No new
temporary App was needed or created for this read-only diagnosis.

The official main App, Codex Framework, renderer helper and service helper are
Developer ID-signed with Team ID `2DC432GLL2` and Hardened Runtime. The main
App contains `Contents/embedded.provisionprofile`. The Phase 8C ad-hoc copy
retained all 14 main entitlement **keys**, but ad-hoc signing did not retain
the certified OpenAI signer chain; its effective entitlement authorization
failed. The previous report did not record the ad-hoc copy's Hardened Runtime
flag or compare all entitlement **values**, so neither is claimed here.
The official bundle's profile cannot authorize a different ad-hoc signer and
was not decoded, copied for this phase, or used to sign anything.

## Main-App entitlement classification

`UNRESTRICTED` here means no provisioning-profile authorization is required
for the entitlement class on macOS. It does **not** mean the capability is
safe, active, or exempt from TCC prompts. `UNKNOWN` means the available Apple
documentation and AMFI event do not establish an independent authorization
classification for that exact key.

| Signed key | Class | Basis |
| --- | --- | --- |
| `com.apple.application-identifier` | UNKNOWN | Signer/profile App ID binding; not named by AMFI |
| `com.apple.developer.aps-environment` | RESTRICTED | macOS push entitlement is profile-assigned |
| `com.apple.developer.team-identifier` | UNKNOWN | Signer/profile identity binding; not named by AMFI |
| `com.apple.security.app-sandbox` | UNRESTRICTED | Sandbox configuration; signed value is `false` |
| `com.apple.security.application-groups` | UNRESTRICTED | Explicit macOS unrestricted class; effective access is separate |
| `com.apple.security.automation.apple-events` | UNRESTRICTED | Hardened Runtime resource-access entitlement; TCC still applies |
| `com.apple.security.cs.allow-jit` | UNRESTRICTED | Hardened Runtime exception |
| `com.apple.security.cs.allow-unsigned-executable-memory` | UNRESTRICTED | Hardened Runtime exception |
| `com.apple.security.device.audio-input` | UNRESTRICTED | Sandbox/Runtime device-access entitlement; TCC still applies |
| `com.apple.security.device.camera` | UNRESTRICTED | Sandbox/Runtime device-access entitlement; TCC still applies |
| `com.apple.security.files.user-selected.read-write` | UNRESTRICTED | Sandbox file-access entitlement |
| `com.apple.security.network.client` | UNRESTRICTED | Sandbox network entitlement |
| `com.apple.security.personal-information.calendars` | UNRESTRICTED | Sandbox personal-information entitlement; TCC still applies |
| `keychain-access-groups` | RESTRICTED | Apple explicitly requires profile authorization |

The renderer helper has 10 signed entitlement keys and the service helper 11,
including `com.apple.security.cs.disable-library-validation` in the service
helper. Neither helper was the Phase 8C rejected executable; helper startup
was never reached. The official main App alone contains the two clearly
profile-dependent claims listed above.

## Decision gate

The observed log proves that preserving the original restricted claims under
an ad-hoc identity cannot launch this App. Preserving the OpenAI Keychain
groups would require signer/profile authorization belonging to that identity;
this phase will not impersonate or reuse it. A theoretically smaller offline
entitlement set is **not yet a validated scheme**: the log does not name a
unique offending key, the prior ad-hoc signature's Hardened Runtime option was
not verified, and no real App startup without login/Keychain access has been
demonstrated. Per the Phase 8D gate, no entitlement is removed and the minimal
signing experiment and live runtime smoke are **not run**.

Verdict: `AMFI_CAUSE_UNCONFIRMED` for the specific unsatisfied key;
`ENTITLEMENT_AUTHORIZATION_FAILED` for the launch failure class.

## Primary sources

- [Apple TN3125: Inside Code Signing — Provisioning Profiles](https://developer.apple.com/documentation/technotes/tn3125-inside-code-signing-provisioning-profiles): macOS unrestricted classes and the restricted-profile distinction.
- [Apple: Creating distribution-signed code for macOS](https://developer.apple.com/documentation/xcode/creating-distribution-signed-code-for-the-mac/): Keychain access groups require a matching provisioning profile, and nested code is signed inside-out.
- [Apple: APS Environment entitlement](https://developer.apple.com/documentation/bundleresources/entitlements/aps-environment): push entitlement value is profile-derived, including the macOS key.
- [Apple: Apple Events entitlement](https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.security.automation.apple-events): Hardened Runtime resource-access classification.
- [Apple: Keychain item sharing](https://developer.apple.com/documentation/security/sharing-access-to-keychain-items-among-a-collection-of-apps): Team-prefixed app identity and Keychain access groups.
- [Apple: Hardened Runtime](https://developer.apple.com/documentation/security/hardened-runtime): runtime protection and exception semantics.
