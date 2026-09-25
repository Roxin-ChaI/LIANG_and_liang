# Liang no Henshin standalone macOS app

This is a separate Electron desktop pet. It uses the approved Gu/Feng v2
atlases and the project's existing one-shot transition engine. It does not
load, patch, sign, or communicate with the Codex Desktop runtime; it does not
read `~/.codex`. Codex event Hooks are not connected.

Build on this Mac with `python tools/build_standalone_app.py`. The resulting
`dist/Liang no Henshin.app` has its own bundle ID and a local ad-hoc signature.
Only that newly built App is signed; the official Codex App is untouched.
Run the App with `open 'dist/Liang no Henshin.app'`, or invoke its executable
directly. The build command refuses to overwrite an existing result.

Left-drag the pet to move it; hover triggers the jumping row. Right-click the
pet for work-state and manual form controls, plus Quit. Automatic form changes
follow Asia/Shanghai weekdays 09:00–12:00 and 14:00–18:00. Startup computes
the current form; system resume reconciles it without replaying missed nodes.
The typed `standalone-app/events.mjs` interface is the extension point for a
future, separately validated Codex-event adapter.

For repeatable real-window verification, run
`python tools/run_standalone_app_qa.py --executable 'dist/Liang no Henshin.app/Contents/MacOS/Electron' --bundled --output standalone-app/evidence/bundled-qa`.
This uses a temporary profile and injected clock, checks actual renderer
frames, captures transparent PNGs, drives a synthetic pointer drag, and then
quits the test instance. `standalone-app/evidence/` and `dist/` are local
generated outputs and are not committed.
