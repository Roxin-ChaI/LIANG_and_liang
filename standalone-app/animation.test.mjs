import assert from "node:assert/strict";
import test from "node:test";
import { ATLAS, CELL, STATES, cellPosition, frameAt, lookState } from "./animation.mjs";

test("v2 atlas geometry and state rows remain exact", () => {
  assert.deepEqual(ATLAS, { width: 1536, height: 2288 });
  assert.deepEqual(CELL, { width: 192, height: 208, columns: 8, rows: 11 });
  assert.equal(STATES.idle.row, 0);
  assert.equal(STATES.running.row, 7);
  assert.equal(STATES.waiting.row, 6);
  assert.equal(STATES.review.row, 8);
  assert.deepEqual(cellPosition(10, 7), { x: -1344, y: -2080 });
});

test("idle loops, while work notifications play three passes then slow idle", () => {
  assert.equal(frameAt("idle", 0).frame, 0);
  assert.equal(frameAt("idle", 280).frame, 1);
  assert.equal(frameAt("idle", 1100).frame, 0);
  for (const [state, pass] of [["running", 820], ["waiting", 1010], ["review", 1030]]) {
    assert.equal(frameAt(state, pass - 1).frame, 5);
    assert.equal(frameAt(state, pass).frame, 0);
    assert.deepEqual(frameAt(state, pass * 3), {
      state: "idle", row: 0, frame: 0, completed: true, slowIdle: true,
    });
    assert.equal(frameAt(state, pass * 3 + 1680).frame, 1);
  }
});

test("an actively held Running task keeps row seven past notification completion", () => {
  for (const elapsed of [0, 819, 820, 2459, 2460, 10_000, 600_000]) {
    const frame = frameAt("running", elapsed, { held: true });
    assert.equal(frame.row, 7);
    assert.equal(frame.state, "running");
    assert.equal(frame.completed, false);
  }
  assert.equal(frameAt("running", 2460).row, 0);
  assert.equal(frameAt("waiting", 3030).row, 0);
});

test("all sixteen look directions preserve ordered v2 rows", () => {
  assert.deepEqual(Array.from({ length: 16 }, (_, index) => lookState(index)),
    Array.from({ length: 16 }, (_, index) => ({
      state: index < 8 ? "look-row-9" : "look-row-10", frame: index % 8,
    })));
});
