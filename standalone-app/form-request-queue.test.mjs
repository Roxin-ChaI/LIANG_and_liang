import test from "node:test";
import assert from "node:assert/strict";
import { createFormRequestQueue } from "./form-request-queue.mjs";

const inFlight = { visualMode: "TRANSITIONING", currentForm: "gu", targetForm: "feng" };
test("animated reverse defers without mutating current operation", () => {
  const queue = createFormRequestQueue();
  assert.equal(queue.consider({ type: "target-form", form: "gu", requestId: "reverse-1" }, inFlight).deferred, true);
  assert.equal(inFlight.targetForm, "feng");
  assert.equal(queue.take().requestId, "reverse-1");
  assert.equal(queue.take(), null);
});
test("latest reverse request replaces older intent, no historical replay", () => {
  const queue = createFormRequestQueue();
  queue.consider({ type: "target-form", form: "gu", requestId: "old" }, inFlight);
  queue.consider({ type: "target-form", form: "gu", requestId: "latest" }, inFlight);
  assert.equal(queue.take().requestId, "latest");
});
test("same active target withdraws reversal without restart", () => {
  const queue = createFormRequestQueue();
  queue.consider({ type: "target-form", form: "gu" }, inFlight);
  assert.equal(queue.consider({ type: "target-form", form: "feng" }, inFlight).deferred, false);
  assert.equal(queue.peek(), null);
});
test("hidden task and interaction updates preserve queued intent", () => {
  const queue = createFormRequestQueue();
  queue.consider({ type: "target-form", form: "gu" }, inFlight);
  assert.equal(queue.consider({ type: "work-state", state: "running" }, inFlight).deferred, false);
  queue.consider({ type: "interaction", kind: "hover", value: true }, inFlight);
  assert.equal(queue.take().form, "gu");
});
test("nonanimated accessibility command remains immediate and clears pending", () => {
  const queue = createFormRequestQueue();
  queue.consider({ type: "target-form", form: "gu" }, inFlight);
  assert.equal(queue.consider({ type: "target-form", form: "gu", animate: false }, inFlight).deferred, false);
  assert.equal(queue.peek(), null);
});
test("normal requests are immediate; invalid values never queue", () => {
  const queue = createFormRequestQueue();
  assert.equal(queue.consider({ type: "target-form", form: "feng" }, { visualMode: "NORMAL" }).deferred, false);
  assert.throws(() => queue.consider({ type: "target-form", form: "other" }, inFlight));
  assert.throws(() => queue.consider({ type: "target-form", form: "gu", animate: "yes" }, inFlight));
});
