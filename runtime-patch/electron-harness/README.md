# Independent Electron runtime harness

This is a project-owned test App, **not** a patched Codex App. It runs the
repository's dual-form source, transition player, oversized overlay, Unix
bridge and Python `FormScheduler` in a real Electron main/preload/renderer
process. It never imports an OpenAI/Codex ASAR or copies a Codex login.

Install the pinned Electron package in this directory with `npm ci`. Electron
39 uses `node node_modules/electron/install.js` to fetch the binary; if the
default release host is unavailable, the public Electron mirror can be set via
`ELECTRON_MIRROR` for that command. The binary and `node_modules` are ignored
by Git.

Run from the repository root using a Python environment with Pillow:

```sh
python tools/run_electron_harness.py --smoke
python tools/run_electron_harness.py
```

The runner copies only the public Electron distribution into a random
`/private/tmp/liang-electron-harness-*` directory, changes its Bundle ID to
`com.liang-no-henshin.runtime-harness`, and ad-hoc signs this **test-only**
App. It uses a minimal test entitlement list with no Keychain access groups.
The temporary App needs the Electron JIT permissions and disables library
validation because the bundled Electron framework retains its upstream
signature; this does not change the system policy or the formal Codex App.
The runner verifies the test Bundle ID, strict structural signature, missing
production Team ID and missing Keychain groups before launch.

The process receives only a temporary HOME, CODEX_HOME, TMPDIR, userData,
sessionData and bridge socket. The bridge socket is private (`0600`), is
removed at shutdown, and is unrelated to Codex private IPC. The runner
terminates only its recorded child PID and deletes the temporary App and user
directories. It retains redacted event logs, screenshots and a report under
`evidence/phase8c/`.

The report's `PROJECT_ELECTRON_HARNESS_PASS` means the project code ran in
Electron, including 10/10 and 8/8 renderer-observed frames, cancellation,
priority, scheduler→Python client→socket→main→preload→renderer, and screenshot
checks. It does **not** prove patched Codex behavior. `capturePage` confirms
renderer pixels near a work-area edge, not physical-screen compositor output;
that remains separately unverified.
