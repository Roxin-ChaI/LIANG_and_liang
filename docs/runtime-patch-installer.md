# Build 9275 runtime patch installer

## Supported target

Phase 7 freezes one exact runtime patch target:

- version `26.908.70816`
- build `9275`
- original `app.asar` SHA256 `100b3a06768326eec58ae32e54fa7b85368fef8d4ead5a5866ecb0e8751bdeaa`
- patch spec `9275.1`

The recipe also pins all seven relevant chunk paths and original SHA256 values. Version, build, archive hash, chunk hash, or exact locator-count mismatch returns `UNSUPPORTED_BUILD` or `LOCATOR_MATCH_COUNT`; there is no fuzzy matching.

## Deterministic patch recipe

`runtime-patch/builds/9275/build-patch.mjs` accepts an extracted read-only input directory and an absent output directory. It copies input into a new tree, verifies every target fingerprint and every locator has exactly one match, then applies ordered project-owned injections. The report records operation ID, target, before/after SHA256, match count, and status without retaining original source excerpts.

The frozen operations provide the dual-form sidecar loader, native fallback, hot atlas source, arbitrary-frame transition descriptor and completion, oversized sibling overlay, stale-operation-token guard, dedicated local bridge service, preload event, overlay subscription, and `requestTargetForm` binding. The existing Codex private `ipc.sock` is never used.

Identical input produces identical patched chunk hashes and a deterministic repacked ASAR. The repository contains locator strings and project-owned injected code, not extracted or patched proprietary chunks.

## Fingerprint and atomic installation

`installer/runtime-patch-installer.py` supports `--dry-run`, `--patch`, `--verify`, and `--restore` against an explicit `--app` path. Phase 7 hard-blocks mutating `/Applications/ChatGPT.app` with `REAL_APP_MUTATION_NOT_AUTHORIZED` and has no bypass flag.

The patch flow is:

1. Validate bundle layout and exact version/build/ASAR/chunk fingerprints.
2. Extract packed ASAR files into a same-filesystem private staging directory.
3. Apply the Build 9275 recipe into a separate patched tree.
4. Parse-check modified JavaScript and validate the operation report.
5. Repack a staged ASAR while preserving the original file-tree metadata and recomputing packed-file offsets and integrity blocks.
6. Re-read every patched target from the staged archive and compare it to the report.
7. Create and verify an installer-owned original backup without overwriting an unknown backup.
8. Atomically replace `app.asar`, verify its installed hash, and atomically write ownership state.

Copy, locator, patch, repack, backup, replacement, verification, or state-write failure restores the exact original ASAR and removes partial state and staging.

## Backup, ownership, idempotence, and restore

The resources directory receives:

- `app.asar.liang-original` — byte-exact verified original.
- `.liang-runtime-patch-state.json` — format version, original version/build/hash, patched hash, and patch-spec version only.

No username, absolute home, or machine-specific path is stored. An existing backup without valid state is refused. A corrupted backup, modified patched archive, or malformed state blocks restore. Reapplying the known patched hash returns `ALREADY_PATCHED` without writes.

Restore stages a verified copy of the backup, atomically replaces the archive, confirms the original SHA256, and then removes only installer-owned state and backup. A restore failure rolls back to the patched ASAR and keeps ownership metadata. ASAR content restore is not signature restore after a re-sign operation.

## App updates

An App update invalidates the old recipe by changing the version/build/archive and usually the chunk names and locators. The 9275 installer safely refuses the currently installed 9922 build. Supporting a new build requires a new read-only recon, exact fingerprints, reviewed locators, recipe tests, temporary-copy smoke, and signing analysis.

## Signing validation and Phase 7B outcome

Build 9922 is frozen as a trusted official baseline in
`runtime-patch/builds/9922/trusted-baseline.json`. The clean-copy smoke copies
only the mounted official App into a private temporary directory, verifies the
copy before mutation, applies the matching installer recipe, records the
expected pre-resign strict-signature failure, preserves the baseline
entitlement keys during ad-hoc signing, and requires deep/strict verification
to pass afterward. It also proves signing leaves the patched ASAR unchanged
and content restore returns the ASAR byte-for-byte to the clean fingerprint.
Content restore does not recreate the original Apple signature.

Phase 7 leaves `/Applications/ChatGPT.app` unchanged, does not launch another App instance, does not modify `~/.codex`, and does not install a daemon. A controlled real install requires a matching audited build and a resolved entitlement-preserving signing strategy.
