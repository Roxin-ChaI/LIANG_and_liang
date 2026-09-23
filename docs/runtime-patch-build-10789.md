# Build 10789 runtime patch migration (Phase 8F)

The source is the [frozen, signed official Build 10789 DMG](current-codex-baseline-cache.md),
not `/Applications/ChatGPT.app`. Historical Build 9275 and 9922 recipes are
unchanged. The new exact-fingerprint recipe is
[`runtime-patch/builds/10789/patch-spec.json`](../runtime-patch/builds/10789/patch-spec.json).

All 12 locators matched **exactly once** in their pinned original chunks:
main avatar loader and bridge registration; preload exposure; core animation
descriptor and completion; overlay source, owner, form commit, sibling layer,
root clip, underlying state and normal-style suppression. The seven chunk
paths and original SHA256 values are frozen in the spec and trusted baseline.
The builder refuses a different build, original ASAR hash, chunk hash, missing
locator, duplicate locator, or in-place output.

The existing deterministic builder was migrated to the new minified symbols
and is applied only to temporary, ignored workspace copies. It retains the
native avatar-loader fallback, one Pet ID, preloaded Gu/Feng atlas sources,
one-shot transition state, operation-token guard, oversized sibling overlay,
and the dedicated local Bridge namespace. Both dry patch runs produced the
same complete ASAR SHA256:

`236cf24c1916e811eea6e55e10591d404b76f8ac1e81974ebe7d845f687e68c0`

The patched raw ASAR header SHA256 is
`1c030d9533cd2ab2c2a5d49d15bcf0c6c4eee308be7344875e2e5d66115f1a73`.
The installer patched only an ignored temporary App copied from the verified
read-only mount. Its `Info.plist` Electron integrity record was updated in
that temporary copy and matches the patched header. The main executable
remained byte-identical to the official source. Installer `--verify` reported
`PATCHED` with the frozen patched hash. No formal Gu/Feng atlas or production
configuration was changed.

Node recipe tests cover all 12 operations, exact source gating, locator
uniqueness, determinism, native fallback, bridge namespace, transition layer
and token guard. These are **structural/static** results; real main, preload,
renderer, Bridge and animation behavior remain `NOT_TESTED` until a safe,
successful minimal-entitlement launch.
