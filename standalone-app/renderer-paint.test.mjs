import test from "node:test";
import assert from "node:assert/strict";
import { rendererHarness, transitionState } from "./test-support/renderer-harness.mjs";

test("actual renderer keeps frame4 acknowledgment when RAF timestamp precedes state epoch", async () => {
  const harness = rendererHarness();
  harness.setNow(100.25);
  await harness.receive(transitionState());
  // A callback timestamp is captured before callbacks execute; it is not the
  // same clock sample as performance.now() in an asynchronous state handler.
  for (let i = 0; i < 7; i++) harness.paint(100, 100.5);
  assert.deepEqual(harness.errors, []);
  assert.ok(harness.reports.some(value => value.transitionFrame === 4));
  assert.ok(harness.pendingCallbacks > 0);
});

test("stale decode/readiness never acknowledges an uncommitted overlay", async () => {
  const h = rendererHarness();
  await h.receive(transitionState());
  h.paint(0); // old readiness has queued its second callback
  const decoding = h.holdDecode("frame-5");
  const incoming = h.receive(transitionState({ frameIndex: 5, overlayImage: "frame-5" }));
  for (let i = 1; i <= 6; i++) h.paint(i * 16);
  assert.equal(h.reports.length, 0);
  decoding.resolve(); await incoming;
  for (let i = 7; i <= 13; i++) h.paint(i * 16);
  assert.ok(h.reports.some(value => value.transitionFrame === 5));
  assert.ok(h.reports.every(value => value.transitionFrame === 5));
});

test("superseded frame4 callback cannot suppress the current frame4 acknowledgment", async () => {
  const h = rendererHarness();
  await h.receive(transitionState());
  for (let i = 1; i <= 3; i++) h.paint(i * 16);
  await h.receive(transitionState({ normalState: "running", underlyingState: "running" }));
  for (let i = 4; i <= 10; i++) h.paint(i * 16);
  assert.ok(h.reports.some(value => value.transitionFrame === 4 && value.state === "running"));
  assert.ok(h.reports.every(value => value.state === "running"));
});

test("decode failure never fakes paint; a subsequent valid state recovers", async () => {
  const h = rendererHarness();
  const image = h.holdDecode("broken");
  const failed = h.receive(transitionState({ overlayImage: "broken" }));
  image.reject(new Error("decode failed")); await failed;
  for (let i = 1; i <= 6; i++) h.paint(i * 16);
  assert.equal(h.reports.length, 0);
  assert.match(h.errors[0].message, /decode failed/);
  await h.receive(transitionState());
  for (let i = 7; i <= 13; i++) h.paint(i * 16);
  assert.ok(h.reports.some(value => value.transitionFrame === 4));
});

test("unexpected sampling exception cannot destroy the RAF chain", async () => {
  const h = rendererHarness();
  await h.receive(transitionState({ normalState: "invalid" }));
  for (let i = 1; i <= 4; i++) h.paint(i * 16);
  assert.ok(h.errors.some(error => error.name === "TypeError"));
  assert.ok(h.pendingCallbacks > 0);
  await h.receive(transitionState());
  for (let i = 5; i <= 11; i++) h.paint(i * 16);
  assert.ok(h.reports.some(value => value.transitionFrame === 4));
});
