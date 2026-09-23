# Phase 8C verdicts

| Target | Verdict | Evidence |
| --- | --- | --- |
| Project-owned Electron app | `PROJECT_ELECTRON_HARNESS_PASS` | `runtime-patch/electron-harness/evidence/phase8c/` |
| Patched Codex App | `REAL_APP_ISOLATION_BLOCKED` | `python tools/isolated_runtime_test.py --audit-real-app` |

The independent test App ran under a temporary Bundle ID, with no production
Keychain groups. Its main/preload/renderer initialized; the private bridge
socket used mode `0600` and was removed on exit. Renderer events showed 10/10
Gu→Feng and 8/8 Feng→Gu frames, one-shot completion, cancellation and stale
operation-token rejection, duplicate no-op, interaction priority, reduced
motion, and five injected scheduler times through the Python client and Unix
socket. Real Electron screenshots and geometry checks showed 224×240 and
208×224 overlays, stable 192×208 normal hitbox and no within-window clipping.
The window was moved to the work-area lower-right edge before `capturePage`;
physical-screen compositor output was not captured, so screen-edge visual QA
is still not fully verified. This is not patched Codex runtime evidence.

The read-only real-App audit found no recognized VM runtime or VM App, and no
other console user session. More importantly, neither a VM listing nor another
user name would establish an *authorized* separate GUI login, separate
Keychain, no single-instance redirection, or a strictly verified temporary
patched App. The gate consequently returns `launchAllowed=false`. No patched
Codex copy was created or started in Phase 8C; the formal App and real
`~/.codex` were not written.

To open the real-App gate in a later phase, provide an already-authorized
independent macOS GUI test VM or login session, then verify from inside it:
distinct user/Keychain and userData, no connection to production Codex IPC,
no single-instance redirection, and the temporary patched App's signed
identity and ASAR integrity. A `sudo -u` process in the current GUI session,
environment variables alone, or a self-declared manifest are insufficient.
