# Build 9275 Local Control Bridge Prototype (Phase 4)

Phase 4 proves a narrow local request path from a project-owned Unix-domain
socket to the already-designed `requestTargetForm()` transition contract. It
does not install or run patched Codex code. The Build 9275 exercise modifies
only temporary copies of the main, preload, and native overlay chunks.

## Transport and security boundary

The v1 transport is newline-delimited JSON over
`$TMPDIR/liang-no-henshin-<uid>/runtime.sock`. The containing directory is
mode `0700`; the socket is owned by the current UID and mode `0600`. Those
filesystem ownership and permission checks are the v1 authentication
boundary—there is no hard-coded bearer token. The server never listens on
TCP and never refers to Codex's private `~/.codex/ipc/ipc.sock`.

Requests are capped at 4096 bytes and strictly limited to protocol version 1,
`setTargetForm`, a bounded request ID, `target` (`gu` or `feng`), and boolean
`animate`. Unknown keys, multiple JSON objects, malformed lines, arbitrary
paths, shell commands, and generic Electron methods are rejected. Duplicate
request IDs reuse the deterministic in-flight/completed result; conflicting
reuse is rejected. Startup safely recovers only a private, current-user stale
socket. Ordinary files and foreign or non-private sockets are never removed.
Shutdown closes clients and removes only the inode the server actually bound.

## Build 9275 insertion contract

The dry-run gates on version `26.908.70816`, build `9275`, app.asar SHA256
`100b3a06768326eec58ae32e54fa7b85368fef8d4ead5a5866ecb0e8751bdeaa`,
and all seven frozen Phase 3E chunk hashes.

| Layer | Exact-one structural seam | Prototype behavior |
| --- | --- | --- |
| Main | Avatar overlay manager construction/registration | Starts the dedicated socket service after `app.whenReady()`, dispatches only fixed target-form payloads to the visible overlay, correlates responses by request ID, and stops on `before-quit`. |
| Preload | Existing `electronBridge` context exposure | Adds independent `window.liangNoHenshin` with only `onSetTargetForm(callback)`. The response send is internal to the preload wrapper; no generic IPC is exposed. |
| Overlay | Selected-avatar render owner | Subscribes once when the overlay runtime is mounted, validates the fixed payload, and delegates to the Phase 3 runtime binding. |
| Runtime binding | `globalThis.__liang9275Runtime?.requestTargetForm` | One match in the combined temporary patch. Build 9275 unpatched source has zero because Phase 3F is also prototype-only; a deployable patch must bundle both contracts together. |

The dedicated Electron channels are
`liang-no-henshin:set-target-form` and
`liang-no-henshin:set-target-form-response`. Main checks that a response comes
from the same overlay `webContents` that received the request. A request ID is
preserved from socket input through main, preload, renderer, and back. Main
waits at most 2000 ms. A missing overlay produces `RUNTIME_NOT_READY`; a silent
renderer produces `RUNTIME_TIMEOUT`; neither is reported as success.

The overlay calls the existing Phase 3 transition state machine only. It does
not reload avatar metadata, invalidate custom-avatar queries, change
`selected-avatar-id`, replace an atlas on disk, or invoke Settings Refresh.
Native Pet state behavior and the existing Settings Refresh implementation are
left byte-for-byte present because no related source site is replaced.

## Dry-run result

All four composite locators matched exactly once in the combined temporary
patch. Static assertions found the dedicated service, project namespace,
fixed IPC names, narrow preload API, renderer-to-runtime delegation,
request-ID response path, 2000 ms timeout, `RUNTIME_NOT_READY`, and preserved
native loader/Refresh-related strings. The patched main, preload, and overlay
copies each passed `node --check`. A project-owned simulation passed request-ID
correlation and timeout behavior.

The real app.asar metadata, SHA256, and all seven frozen chunk hashes were
identical before and after the run. Original and patched proprietary chunk
copies were removed with the one temporary directory. No code from a
proprietary chunk was imported or executed.

## Deployment boundary and remaining risks

The main helper assumes a future authorized bundling step will supply the
reviewed `createBridgeServer` factory from `runtime-patch/bridge/server.mjs`.
The installed Build 9275 currently has neither that factory nor the Phase 3F
transition runtime. Consequently the successful dry patch is a structural and
syntax proof, not live App control. A future patch must bundle both pieces,
verify Electron lifecycle ordering, surface safe startup failures without an
unhandled rejection, and confirm that `before-quit` allows asynchronous socket
cleanup to finish. It must also re-run fingerprint gates after any App update.

No App patch, codesign, LaunchAgent, daemon, UI automation, private IPC reuse,
or `~/.codex` mutation is performed in Phase 4.
