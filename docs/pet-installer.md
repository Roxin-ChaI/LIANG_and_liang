# Liang Pet installer prototype

Phase 6 packages and validates the existing Liang Wengu and Liang Wenfeng assets as one deterministic Codex Pet payload. It also provides an ownership-aware installer that is intentionally restricted to fake Codex homes during this phase.

## Build the payload

```sh
node installer/pet-payload.mjs --output build/pet-payload
```

The generated directory is `build/pet-payload/liang-no-henshin/`. It contains:

- `pet.json` — native Codex Pet v2 metadata for the single ID `custom:liang-no-henshin`.
- `spritesheet.webp` — byte-identical Liang Wengu fallback for an unpatched runtime.
- `forms/gu/spritesheet.webp` and `forms/feng/spritesheet.webp` — the two approved 1536×2288 RGBA v2 atlases.
- `liang-runtime.json` — dual-form and transition metadata for the later runtime patch.
- `transitions/gu_to_feng/` and `transitions/feng_to_gu/` — normalized RGBA transition overlay frames.
- `.liang-install-manifest.json` — sorted SHA256 inventory of every payload file other than the manifest itself.

The builder validates source dimensions, frame counts, transition geometry, hashes, fallback identity, and schema semantics. It refuses to overwrite an existing payload directory. Repeated builds in distinct output roots are byte-for-byte deterministic. `build/pet-payload/` is ignored because it is reproducible from versioned sources.

## Native fallback and runtime sidecar

The native fallback always loads the approved Gu atlas. This keeps the Pet usable when no runtime patch is present. The sidecar does not change the native Pet contract; it supplies the future patched runtime with Gu/Feng atlas paths, initial form, ordered transition frames, frame timing, and oversized overlay anchor geometry.

## Preview an installation

All Phase 6 verification must use an explicit fake Codex home:

```sh
python tools/install_liang_pet.py \
  --codex-home /tmp/liang-test/.codex \
  --payload build/pet-payload/liang-no-henshin \
  --dry-run
```

Dry-run returns JSON with `INSTALL`, `UPDATE`, `ALREADY_CURRENT`, or `REFUSE`, together with the destination, Pet ID, and anticipated config mutation. It performs zero writes.

## Atomic install flow

`--install` validates the source payload before creating or modifying destination state. It then:

1. Creates a staging directory beside the destination, on the same filesystem.
2. Copies the payload and verifies the complete manifest and every SHA256.
3. Writes `.liang-install-state.json` and flushes staged files.
4. Renames an owned existing installation to a private backup when updating.
5. Atomically renames staging to `pets/liang-no-henshin`.
6. Minimally patches `[desktop].selected-avatar-id` in `config.toml`.
7. Revalidates installed ownership and hashes before deleting the backup.

Any copy, hash, rename, or config-write failure restores the original Pet and config and removes staging. The installer never deletes or modifies another Pet.

## Ownership model

An existing Liang destination is replaceable or removable only when both files are valid:

- `.liang-install-manifest.json` must describe the exact installed file set and hashes.
- `.liang-install-state.json` must identify `custom:liang-no-henshin`, bind to that manifest hash, and retain the avatar selected before the first Liang install.

An unknown or modified destination is refused with `REFUSE_UNOWNED_DESTINATION`; there is no `--force` option. Updates preserve the original pre-install avatar rather than recording Liang as its own predecessor.

Payload roots, destination directories, the `pets` directory, and `config.toml` must not be symlinks. Manifest paths must be relative, remain within the payload root, and enumerate only regular files.

## Config patch and uninstall

The config patch is textual and deliberately narrow. It creates `[desktop]` only when missing, otherwise changes or inserts only `selected-avatar-id`. Comments, quoting style, unrelated desktop keys, and unrelated sections remain intact.

`--uninstall` verifies ownership before atomically moving the Pet aside. It restores the previous avatar selection, or removes the key it added when no previous selection existed. Other config and Pets remain untouched. Failure during config restoration puts the Pet back.

## Real-home safety gate

Phase 6 rejects mutating operations whenever `--codex-home` resolves to the real `~/.codex`:

```text
REAL_HOME_INSTALL_NOT_AUTHORIZED
```

There is intentionally no override flag. Dry-run may inspect the real path, but install and uninstall cannot mutate it. Real installation authorization belongs to a later integration phase.

## Verification

```sh
node --test installer/pet-payload.test.mjs
python -m pytest tests/test_install_liang_pet.py tests/test_pet_installer_e2e.py
```

The tests build fresh payloads and use temporary fake Codex homes. They cover deterministic packaging, clean install, update, idempotence, config preservation, ownership refusal, uninstall, symlink/path security, injected failures, rollback, real-home blocking, and dry-run zero writes.

## Phase 6 limitations

This phase does not patch the Codex renderer or state machine, install the scheduler as a daemon, touch the real `~/.codex`, modify or sign `ChatGPT.app`, invoke private IPC, or enable live Gu/Feng transitions. It validates only deterministic packaging and safe installer behavior.
