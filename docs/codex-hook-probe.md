# Codex lifecycle hook probe (Standalone Phase 2)

Official contract: <https://learn.chatgpt.com/docs/hooks>. This project uses only
`<repo>/.codex/hooks.json`; it does not modify user-level Codex configuration.
Each command hook sends only `event`, `session_id`, and a UTC timestamp to a
project-local Unix socket. The collector discards every other input field,
including prompt text, tool arguments/results, transcript paths and credentials.
Hooks emit no stdout/stderr and exit successfully if the receiver is absent.
The events are advisory and do not approve, block or rewrite Codex operations.

## Environment and evidence

- Read-only inspection: official Desktop app `26.917.71314` (Build `10954`);
  `codex-cli 0.153.4`.
- No pre-existing project hook config or user `hooks.json` was found. User-level
  `config.toml` was not changed.
- A hand-fed receiver smoke test delivered only the three permitted fields.
  The ignored log is `.cache/codex-events.jsonl`.
- One read-only CLI control invocation with the project hooks (one-off audited
  hook-trust bypass) observed `SessionStart`, `UserPromptSubmit`, `SessionEnd`.
  The model request timed out before any tool call, so this control did not
  exercise `PreToolUse`, `PostToolUse`, `PermissionRequest`, or `Stop`.
- **Desktop hook execution remains NOT_VERIFIED.** The current Desktop task did
  not reload/trust the newly added project hook configuration during the
  ongoing turn. No Desktop event is present in the probe log. The app's UI
  automation surface also denied access to `com.openai.codex`; no automated
  trust decision or Desktop task was fabricated.

| Event | Officially documented | CLI control | Desktop actual |
| --- | --- | --- | --- |
| SessionStart | yes | observed | NOT_VERIFIED |
| UserPromptSubmit | yes | observed | NOT_VERIFIED |
| PreToolUse | yes | NOT_VERIFIED | NOT_VERIFIED |
| PostToolUse | yes | NOT_VERIFIED | NOT_VERIFIED |
| PermissionRequest | yes | NOT_VERIFIED | NOT_VERIFIED |
| Stop | yes | NOT_VERIFIED | NOT_VERIFIED |
| SessionEnd | yes | observed on CLI interruption | NOT_VERIFIED |

No Desktop trigger latency can honestly be calculated until this project's
hooks are reviewed/trusted and a new Desktop turn actually runs. The CLI
control does not substitute for that acceptance gate.
