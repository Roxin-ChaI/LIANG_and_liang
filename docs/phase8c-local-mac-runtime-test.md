# Phase 8C controlled local Mac test (Build 9922)

The same-user test was explicitly authorized. It does **not** prove Keychain
separation. No production Keychain item was read or copied, and no permission
or login prompt was approved.

## Verified preparation

- Official App: `/Applications/ChatGPT.app`, version `26.915.31945`, Build
  `9922`; running main PID at start: `52646`.
- Official `app.asar` SHA256:
  `1f7939c1c781887c167043c4d1d307af3400d324685cfc315dfe2f80e634f483`.
- Official strict signature and Gatekeeper preflight: PASS.
- A separate temporary App was copied, patched with the frozen 12-locator
  recipe and verified at ASAR SHA256
  `9bc7617d644161f7f574439d85710f3b8dede34a62255e6d390a21736fc8502e`.
- Patched Electron raw-header integrity SHA256 was written to the temporary
  `Info.plist`: `a091e0faf35246766ec150a38dc8b394e857305a46b1757c54301ececf474e65`.
- All 14 entitlement **keys** were retained. Ad-hoc signing and `codesign
  --verify --deep --strict` passed. This did not retain the original Apple
  Developer Team authority or prove effective Keychain access.
- A Phase 6 Pet payload was installed only to temporary `CODEX_HOME`. The
  temporary userData and socket namespace were distinct from production.

## Actual executable launch

Two controlled launch attempts of the temporary App executable exited before
main initialization; the detached attempt produced no stdout/stderr bytes and
created no runtime socket. The official Codex process remained running.
Narrowly filtered macOS diagnostics for the temporary PID reported:

> AppleMobileFileIntegrityError Code=-424: The file is adhoc signed but contains restricted entitlements

This is a launch-level AMFI rejection, not a transition or Bridge assertion.
The temporary copy also failed Gatekeeper assessment as expected for this
ad-hoc identity. We did not remove entitlement keys, disable AMFI/Gatekeeper,
auto-approve a prompt, reuse credentials, or attempt a production-App patch.

## Verdicts

- Temporary App signing/integrity preparation: PASS.
- Patched Codex main/preload/renderer launch: BLOCKED by AMFI.
- Real Bridge, both transitions, overlay/hitbox, scheduler E2E and visual QA:
  NOT RUN / UNCONFIRMED.
- Independent project-owned Electron harness: previously PASS, but not
  evidence for patched Codex.
- `READY_FOR_DEPLOYMENT`: NO.

To resume real-App testing without weakening macOS protections, use a valid
signing identity and provisioning/entitlement arrangement authorized for the
temporary App, or revise the test contract to a separately reviewed entitlement
set. Neither path was authorized or attempted in this phase.
