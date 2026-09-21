# Clean official Codex runtime baseline gate

## Purpose

Phase 7B treats the currently installed `/Applications/ChatGPT.app` as an
**UNTRUSTED_REFERENCE**. Build 9922 in that bundle has an actual `app.asar`
SHA256 of
`1f7939c1c781887c167043c4d1d307af3400d324685cfc315dfe2f80e634f483`,
while its `ElectronAsarIntegrity` metadata expects
`a2c8179f53b4722a1d847ccd1753ad60fae8a84a08caf3b40f360edeac6a0a9a`.
Strict code-signature verification fails and its XML entitlement blob is
malformed. It therefore cannot supply production hashes, signing material,
entitlements, or a deployment target.

The Build 9922 recipe under `runtime-patch/builds/9922/` remains a
**STRUCTURAL_MIGRATION_PROBE** until it is reconstructed or revalidated
against a clean official App with matching ASAR integrity.

## Read-only tools

`tools/find_clean_codex_reference.py` searches only these local locations:

- mounted `/Volumes/*/ChatGPT.app` and `/Volumes/*/Codex.app`;
- `~/Downloads/ChatGPT*.app` and `~/Downloads/Codex*.app`;
- `~/Desktop/ChatGPT*.app` and `~/Desktop/Codex*.app`;
- every explicitly supplied `--app <path>`.

It does not use the network, mount images, install an App, replace the
installed App, or select a candidate by filename alone. Every discovered
candidate is passed to `tools/validate_clean_codex_reference.py`. The exact
installed `/Applications/ChatGPT.app` is always rejected as a clean source,
including when explicitly supplied.

Run discovery with:

```bash
python3 tools/find_clean_codex_reference.py
```

Validate a specific mounted or copied candidate with:

```bash
python3 tools/validate_clean_codex_reference.py --app /path/to/ChatGPT.app
```

Both tools print JSON to stdout. They do not write reports or modify the
candidate. A before/after tree snapshot plus hashes of `Info.plist`, the main
executable, `app.asar`, and `CodeResources` enforce the zero-mutation gate.

## Clean-reference contract

A candidate is accepted only when all of these checks pass:

1. It is a real, non-symlink App directory with `Info.plist`, the declared
   main executable, `Resources/app.asar`, and `_CodeSignature/CodeResources`.
2. Its bundle identifier is `com.openai.codex`.
3. `lipo` can report at least one executable architecture.
4. `codesign --verify --deep --strict --verbose=4` passes.
5. Gatekeeper assessment passes.
6. Every discovered executable/nested `.app`, `.framework`, `.xpc`,
   `.dylib`, and `.node` candidate passes strict component verification.
7. The main signature advertises hardened runtime.
8. `codesign` can emit the main entitlements as a valid XML plist.
9. `ElectronAsarIntegrity` contains a SHA256 record for
   `Resources/app.asar`, and the expected digest equals the actual digest.
10. The codesign identifier, Team ID, and system-reported authority chain
    match the expected official identity.

The secondary Team ID check currently uses `2DC432GLL2`, which Phase 7A
directly observed in the signed Build 9922 CodeDirectory. It is not sufficient
on its own: strict codesign, Gatekeeper, an authority chain, hardened runtime,
nested signatures, valid entitlements, and ASAR integrity must also pass. No
unverified Team ID or filename can make a candidate trusted.

## Classifications

Each candidate receives exactly one primary classification:

- `CLEAN_REFERENCE_PASS`
- `REJECT_SIGNATURE`
- `REJECT_ASAR_INTEGRITY`
- `REJECT_ENTITLEMENTS`
- `REJECT_IDENTITY`
- `REJECT_STRUCTURE`

Discovery returns `CLEAN_REFERENCE_PASS` when one or more independently
validated candidates pass. It returns `CLEAN_REFERENCE_INVALID` when local
candidates exist but all fail. When no candidate exists, it returns
`CLEAN_OFFICIAL_APP_REQUIRED`.

If a clean reference is found, the discovery output includes only a read-only
difference summary against the untrusted installed App: version/build, actual
and expected ASAR hashes, strict-signature status, and changed hashes for the
main executable, `Info.plist`, `app.asar`, and `CodeResources`. It never tries
to repair or synchronize either bundle.

## Gate A and next action

Phase 7B stops after this validator commit unless discovery produces
`CLEAN_REFERENCE_PASS`. A missing reference is an expected gate outcome, not
a test failure. Obtain a new official Codex Desktop distribution without
overwriting the installed App, then leave its App mounted from the official
DMG or copy it under a distinct name such as
`~/Downloads/ChatGPT-clean.app` and rerun discovery.

Only a passing clean reference may proceed to trusted build fingerprinting,
clean locator recon, temporary-ASAR patching, and temporary-copy ad-hoc
signing validation. Official App, ASAR, extracted proprietary JavaScript, and
entitlement blobs are never committed to this repository.
