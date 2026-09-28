import test from "node:test";
import assert from "node:assert/strict";
import { createPaintAckGate } from "./paint-ack.mjs";

function harness() {
  let serial = 1;
  const callbacks = [], sent = [];
  let fail = false;
  const report = createPaintAckGate({ schedule: fn => callbacks.push(fn),
    currentSerial: () => serial,
    send: payload => { if (fail) throw new Error("send failed"); sent.push(payload); } });
  return { report, sent, paint: () => callbacks.splice(0).forEach(fn => fn()),
    serial: value => { serial = value; }, fail: value => { fail = value; } };
}

test("paint gate delivers once after two paint boundaries, not when queued", () => {
  const h = harness(), value = { serial: 1, key: "frame4", payload: 4 };
  assert.equal(h.report(value), true);
  assert.equal(h.report(value), false);
  h.paint(); assert.deepEqual(h.sent, []);
  h.paint(); assert.deepEqual(h.sent, [4]);
  assert.equal(h.report(value), false);
});

test("stale paint cannot poison delivery of the same frame in a new generation", () => {
  const h = harness();
  h.report({ serial: 1, key: "frame4", payload: "old" });
  h.paint(); h.serial(2);
  h.report({ serial: 2, key: "frame4", payload: "new" });
  h.paint(); assert.deepEqual(h.sent, []);
  h.paint(); assert.deepEqual(h.sent, ["new"]);
});

test("failed transport delivery remains retryable and does not acknowledge", () => {
  const h = harness(), value = { serial: 1, key: "frame4", payload: 4 };
  h.fail(true); h.report(value); h.paint();
  assert.throws(() => h.paint(), /send failed/);
  h.fail(false); assert.equal(h.report(value), true);
  h.paint(); h.paint(); assert.deepEqual(h.sent, [4]);
});
