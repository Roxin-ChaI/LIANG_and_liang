# Frame acknowledgment stall investigation

## Evidence and confidence

The 24b0df1 live failure published Gu→Feng frame 4 after a Waiting / Hover /
Review / hover-leave burst, but received no paint acknowledgment for that frame.
Main correctly did not start its 140 ms timer without that acknowledgment.
The original trace has no renderer exception stack. Its exact historical
exception is **NOT_PROVEN**, not retrospectively confirmed by a unit test.

Two bounded old-renderer runs with new TEST-only console-error capture completed
normally (`standalone-app/evidence/v010-asset-rework/diagnosis-{1,2}`). Neither
recorded a renderer error. This is an intermittent defect, not proof of absence.

`player/frame4-reproduction.json` compares the actual baseline renderer and fixed
renderer using an injectable RAF/decode/clock unit harness. Under the tested
ordering, RAF's batch timestamp is earlier than the asynchronously committed
animation epoch. Baseline `frameAt` throws `RangeError`; the only RAF chain never
requeues; frame 4 is never acknowledged and main waits indefinitely. This
failure mechanism is **CONFIRMED by deterministic reproduction**, but the
ordering is injected, not a captured historical live clock measurement.

## Other confirmed unsafe orderings

- A superseded state's double-RAF readiness callback could set `imageReady`
  while a newer overlay was still decoding.
- Deduplication recorded a report as delivered before its asynchronous paint
  callback ran. Supersession could drop the callback after bookkeeping had
  already treated it as reported. Reports lacked operation-token identity.
- A rejected decode promise remained cached; an exception while sampling could
  terminate the sole RAF chain. These are directly tested source-code paths.

## Repair scope

Only the project-owned renderer, paint-ack helper and build manifest change.
Normal animation age starts at zero if its epoch is newer than the RAF batch.
RAF always requeues in `finally`, without inventing an acknowledgment. Decode
and readiness are generation-guarded. Failed decode never fakes paint and is not
permanently cached. Paint deduplication occurs after successful delivery, scoped
to renderer generation and operation token. Stale work cannot poison delivery
of the same frame in the new generation.

Main's existing token/frame checks and paint→140 ms dwell→advance contract are
unchanged. All 10/8 transition frames remain; no watchdog skip, faster playback,
replacement images or transition-art edits were introduced. TEST-only console
errors are recorded for future live diagnosis, not used to advance animation.

## Verification

- Eight new Node tests execute actual renderer source / paint gate: negative
  clock ordering, stale decode/readiness, stale frame4 callback, decode failure,
  sampling recovery, post-paint delivery, deduplication and failed transport.
- Builder tests: 2 PASS; helper is packaged, unit harness is not.
- Actual isolated AckFix App's first race run: both directions complete, reverse
  queued at frame4, state burst completes, latest Review restored. This is a
  live project Electron test, not a synthetic Hook/Desktop integration claim.
- Integrated frame-by-frame and repeated live runs are recorded separately in
  Commit 4. No finite test suite proves all possible future stalls impossible.

Transition art remains `NEEDS_MANUAL_ART_REDESIGN`. Player improvement must not
be reported as an endpoint artwork or overall visual PASS.
