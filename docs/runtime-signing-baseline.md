# Current Codex signing baseline diagnosis (Build 9922)

## Scope

This Phase 7A diagnosis is read-only. It inspected
`/Applications/ChatGPT.app` with `codesign`, `spctl`, `xattr`, plist parsing,
SHA256 comparison, and per-component verification. It did not sign, copy,
replace, chmod, chown, remove quarantine from, or otherwise mutate the
installed application. A before/after tree snapshot and hashes of the main
executable, `Info.plist`, `app.asar`, and `CodeResources` were identical.

The diagnostic implementation is `tools/diagnose_codex_signing.py`. Its
command runner is injectable so malformed output, missing commands, main and
nested failures, and mutation detection can be tested without touching a
real app bundle.

Confidence labels mean:

- **CONFIRMED**: directly observed and reproducible on this installed bundle.
- **LIKELY**: supported by evidence but not uniquely attributable.
- **UNKNOWN**: the available local evidence cannot establish the claim.

## Frozen bundle identity

| Field | Value | Confidence |
| --- | --- | --- |
| Bundle identifier | `com.openai.codex` | CONFIRMED |
| Version | `26.915.31945` | CONFIRMED |
| Build | `9922` | CONFIRMED |
| Architecture | `arm64` | CONFIRMED |
| Main executable SHA256 | `dfe5654498e939d355702fa66e6e2400e55ec0ade61048e19e264f4bdc70b847` | CONFIRMED |
| `app.asar` SHA256 | `1f7939c1c781887c167043c4d1d307af3400d324685cfc315dfe2f80e634f483` | CONFIRMED |
| `Info.plist` SHA256 | `c2fb3359c596b749c548766c6a9b5a643511be08f43a98504de2a5586a385626` | CONFIRMED |
| `CodeResources` SHA256 | `f5cf6ea3e1e015083237f9f6fab76dd5b37e34c94eaa503e0395c8d2b71a9328` | CONFIRMED |

## Strict verification and signing metadata

`codesign --verify --deep --strict --verbose=4` returned 1 with:

```text
/Applications/ChatGPT.app: invalid signature (code or signature have been modified) In architecture: arm64
```

`codesign -dv --verbose=4` could still read the signature container. It
reported TeamIdentifier `2DC432GLL2`, hardened-runtime flags, a stapled
notarization ticket, unavailable authority output, and `Info.plist` not
bound. Readability of the CodeDirectory is not evidence that strict
verification passes.

The per-component pass checked the main bundle plus 89 nested candidates.
The main bundle was the first failing component. Totals were 0 passing, 44
failing, and 46 reported unsigned. This confirms widespread baseline signing
failure, but the deep verification output did not identify one unique nested
component as the originating cause.

Gatekeeper assessment returned 1 with an internal Code Signing subsystem
error. That is consistent with an untrusted baseline but is not used as the
root-cause classifier.

## Entitlements diagnosis

The diagnostic intentionally tried both current and legacy display forms:

- abstract `codesign --display --entitlements -`: return 0, 1162 bytes;
- DER `codesign --display --entitlements - --der`: return 0, 794 bytes;
- XML `codesign --display --entitlements - --xml`: return 0, no plist, with
  `binary contains an invalid entitlements blob`;
- deprecated legacy `--entitlements :-`: the same invalid-blob warning plus
  the expected deprecation warning.

Classification: **`MALFORMED_XML_BLOB` (CONFIRMED)**. This is not explained
by using only the deprecated colon syntax: the proper XML request produces
the same invalid-blob result while abstract and DER forms remain readable.
It is also distinct from a bundle with no entitlements.

Because no valid XML entitlement plist can be preserved, a temporary-copy
signing experiment is **`TEMP_SIGNING_EXPERIMENT_BLOCKED`**. Phase 7A does
not guess, normalize, or synthesize replacement entitlements.

## ASAR integrity diagnosis

`Info.plist` records this expected `ElectronAsarIntegrity` SHA256 for
`Resources/app.asar`:

```text
a2c8179f53b4722a1d847ccd1753ad60fae8a84a08caf3b40f360edeac6a0a9a
```

The actual archive SHA256 is:

```text
1f7939c1c781887c167043c4d1d307af3400d324685cfc315dfe2f80e634f483
```

Classification: **`ASAR_INTEGRITY_MISMATCH` (CONFIRMED)**. The current
archive content differs from the digest embedded in the bundle metadata.
This proves that the installed app is not a trustworthy clean signing
baseline. Local evidence does not identify who changed it or when.

## Cause matrix

| Candidate category | Result | Evidence |
| --- | --- | --- |
| A. Historical app-content modification | CONFIRMED in effect; actor/time UNKNOWN | Actual `app.asar` differs from embedded integrity digest. |
| B. Nested signature abnormality | CONFIRMED; unique nested root UNKNOWN | Main plus 43 nested candidates fail strict component verification; 46 candidates are unsigned. |
| C. ASAR integrity mismatch | CONFIRMED | Expected and actual SHA256 values differ. |
| D. Entitlement command misuse | REJECTED as primary explanation | Proper XML and deprecated legacy requests both report the invalid blob. |
| E. Download/quarantine/xattr issue | UNKNOWN and not causal evidence | Only ordinary provenance/metadata attributes were observed; no write or removal was attempted. |
| F. Malformed XML entitlement blob | CONFIRMED | Abstract/DER data exists, but no valid XML plist can be extracted. |

No Liang patch backup, state file, or similarly named patch remnant was found
inside the bundle. Modification times are recorded only as context and are
not used to infer causality. No separate clean `com.openai.codex` app bundle
was available under the searched local application roots, so clean-reference
comparison is **`CLEAN_REFERENCE_UNAVAILABLE`**.

## Result

- Cause classification: **`BASELINE_SIGNING_CAUSE_CONFIRMED`**.
- Confirmed causes: **`ASAR_INTEGRITY_MISMATCH`** and
  **`MALFORMED_XML_ENTITLEMENTS_BLOB`**.
- Real bundle mutation during diagnosis: **none**.
- Clean comparison reference: **unavailable**.
- Temporary-copy signing experiment: **blocked**, because valid XML
  entitlements cannot be preserved.
- Phase 7A signing verdict: **`CURRENT_APP_BASELINE_UNTRUSTED`**.

This verdict does not block creating or statically testing a Build 9922 patch
recipe against a temporary ASAR tree. It does block claiming that the current
installed app supplies a known-good signing baseline or that a safe signing
recipe has been established.
