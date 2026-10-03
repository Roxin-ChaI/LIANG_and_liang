import test from "node:test";
import assert from "node:assert/strict";
import { createDragDirection } from "./drag-direction.mjs";
import { frameAt } from "./animation.mjs";
import { rendererHarness } from "./test-support/renderer-harness.mjs";

test("slow 1px motion accumulates and repeated direction is not republished", () => {
  const drag = createDragDirection();
  assert.deepEqual([drag(1), drag(1), drag(1), drag(1), drag(20)],
    [null, null, null, "running-right", null]);
});
test("jitter does not reverse animation; genuine reversal does", () => {
  const drag = createDragDirection();
  assert.equal(drag(10), "running-right");
  assert.equal(drag(-1), null);
  assert.equal(drag(1), null);
  assert.equal(drag(-8), "running-left");
  assert.equal(drag(-100), null);
  assert.equal(createDragDirection()(-4), "running-left");
});
test("both drag loops have uniform dwell including frame 8 and wrap", () => {
  for (const state of ["running-left", "running-right"]) {
    for (let i = 0; i < 24; i++) {
      assert.equal(frameAt(state, i * 120).frame, i % 8);
      assert.equal(frameAt(state, i * 120 + 119).frame, i % 8);
    }
  }
});

test("actual renderer accumulates slow drag, filters jitter and clears on release", () => {
  const h = rendererHarness();
  h.pointer("pointerdown", {screenX: 100, screenY: 100});
  for (const x of [101,102,103,104,103,104,102,100,98,96]) {
    h.pointer("pointermove", {screenX: x, screenY: 100});
  }
  h.pointer("pointerup");
  assert.deepEqual(h.interactions.map(e => e.value), ["running-right", "running-left", null]);
  assert.equal(h.moves.reduce((sum, p) => sum+p.x, 0), -4);
});
