# Liang no Henshin Runtime Patch Contract

This document freezes the Phase 1 contract for adding dual-form visuals to
`custom:liang-no-henshin`. It is a design and reference-test boundary only. It
does not patch, install, sign, or communicate with Codex Desktop.

## 1. Native compatibility

The native `pet.json` remains unchanged and authoritative for an unpatched
Codex runtime. Dual-form metadata lives in a sibling `liang-runtime.json`
sidecar. A runtime that does not know this sidecar continues to load the pet as
an ordinary single-atlas custom pet. If the sidecar is absent, unreadable, or
unsupported, a patched runtime must preserve that same native behavior.

The sidecar may augment a successfully loaded native pet but never replace its
identity, Pet ID, display name, sprite version, or native validation. In
particular, `custom:liang-no-henshin` remains one Pet ID.

## 2. Runtime sidecar schema

Sidecar schema version 1 is formally defined by
`runtime-patch/schema/liang-runtime.schema.json`. It requires both `gu` and
`feng` atlas sources and the two directed transitions. The repository fixture
uses the current formal atlas files and every current transition frame in
filename order.

All sidecar paths are interpreted relative to the containing Pet root. A path
must be a non-empty, forward-slash relative path. Absolute POSIX paths,
Windows drive paths, backslashes, empty segments, `.` segments, and `..`
segments are invalid. After joining a path to the Pet root, the loader must
also perform a canonical containment check before reading it. Schema checks do
not replace filesystem containment checks.

The loader must reject unknown schema versions, forms other than `gu` and
`feng`, missing form atlases, empty transition frame arrays, non-positive or
non-integral frame durations, illegal transition endpoints, and unknown
properties.

## 3. Form model

`Form` is exactly `gu | feng`. The overlay-owned runtime state contains at
least:

```text
currentForm       last atomically committed form
targetForm        requested destination form
selectedSource    atlas paired with currentForm
playbackEpoch     renderer-remount/reset generation
underlyingState   latest native task/interaction state
reducedMotion     current accessibility preference
```

The visual layer has exactly two modes: `NORMAL` and `TRANSITIONING`.
Transition names are not added to the native `idle`, `running`, `waiting`,
`review`, or other task-state enum.

## 4. Transition model

A transition is a separate, arbitrary-frame, one-shot visual layer. Direction
is derived from the committed form and requested target:
`gu_to_feng` or `feng_to_gu`. Frames play once, in listed order, for
`frameDurationMs` each. The renderer must expose completion with the operation
token that started playback.

Visual priority is:

```text
TRANSITION > drag transient > hover jumping > task notification > idle/look
```

While `TRANSITIONING`, hover, drag, and look input cannot replace transition
frames. Task notifications may update `underlyingState` without changing the
active transition. Completion returns to `NORMAL` and renders the latest
underlying state, not the state captured when the transition began.

## 5. Reduced-motion behavior

When reduced motion is true,
`setTargetForm({ target, animate: true, ... })` performs a direct atomic form
commit. No transition frames are decoded or played. This behavior is also used
when `animate` is explicitly false.

## 6. Error and fallback behavior

- If the target atlas is unavailable or invalid, reject the request and keep
  the complete current form/source/epoch tuple unchanged.
- If the target atlas is valid but the required transition is unavailable or
  invalid, atomically commit the target without animation and report
  `transitionFallback: true`.
- If the requested target is already the committed form and there is no
  conflicting active transition, accept a no-op without changing the source
  or playback epoch.
- A malformed command is rejected without state mutation.
- Failure to load or validate the sidecar falls back to the untouched native
  single-pet path.

## 7. Atomic form switching

A form commit is one renderer transaction that changes `currentForm`,
`targetForm`, and `selectedSource`, and increments `playbackEpoch` exactly
once. Consumers must never observe a new form paired with the old atlas or an
old form paired with the new atlas. Rejected, duplicate, cancelled, and stale
operations do not increment `playbackEpoch`.

In the eventual renderer, `playbackEpoch` must key or reset frame playback so
the new atlas starts at a valid frame boundary without Settings > Pets >
Refresh.

## 8. Operation-token semantics

Every newly started or superseding operation receives a unique token. Only
`completeTransition(activeToken)` may commit its target. A completion carrying
an older, cancelled, or otherwise non-active token is a no-op.

A duplicate request for the active target does not restart playback or mint a
token. A reverse request during a transition supersedes the active operation,
mints a new token, and recomputes from the last committed form. Because the
old target was never committed, reversing to the committed form cancels the
visual transition without a form commit. The superseding token makes a late
old completion harmless. Explicit cancellation follows the same invalidation
rule.

## 9. Bridge command contract

The logical command is:

```js
setTargetForm({
  target: "gu" | "feng",
  animate: boolean,
  requestId: string,
})
```

Every response preserves `requestId` and includes:

```js
{
  accepted: boolean,
  currentForm: "gu" | "feng",
  targetForm: "gu" | "feng",
  transitioning: boolean,
  requestId: string,
}
```

Implementations may add result metadata such as `noOp`, `reason`,
`operationToken`, or `transitionFallback` without changing those required
fields. Phase 1 intentionally does not choose socket, localhost, Electron IPC,
or any other transport.

## 10. Security and trust boundary

Native manifest validation remains mandatory. A future main-process loader is
responsible for schema validation, canonical path containment, file type and
atlas-dimension validation, transition image validation, and producing trusted
renderer-safe sources. The renderer must not receive arbitrary filesystem
access or accept arbitrary paths from bridge callers.

Bridge callers may select only a form and animation preference; they may not
supply asset paths, frame data, JavaScript, or native task state. `requestId`
is correlation data, not authorization. Authentication, replay limits,
lifecycle ownership, and the final external transport remain unresolved until
a later threat-modelled phase. Codex's existing private `ipc.sock` is outside
this contract.

## 11. Phase 2 implementation boundary

Phase 2 may prototype a dual-atlas loader/model and overlay-owned form state
against an isolated, reproducible build. Its narrow source-selection point is
immediately before the overlay converts the selected avatar option into the
core renderer source. It may add arbitrary one-shot playback plus a completion
callback and then evaluate a typed main/preload bridge.

Phase 2 must retain the same Pet ID, preserve all native task rows and look
behavior, gate itself on the recorded build fingerprints, and test memory and
decode costs. This contract does not authorize editing the active
`/Applications/ChatGPT.app`, `app.asar`, `~/.codex`, signatures, launch agents,
background services, real Electron IPC, or private Codex IPC.
