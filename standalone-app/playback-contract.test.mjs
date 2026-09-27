import assert from "node:assert/strict";
import test from "node:test";
import { isCurrentTransitionPaint, shouldRestartPlayback } from "./playback-contract.mjs";

test("duplicate Running and hidden task updates preserve the visible playhead", () => {
  assert.equal(shouldRestartPlayback({ normalState: "running" }, { normalState: "running" }), false);
  assert.equal(shouldRestartPlayback({ normalState: "jumping" }, { normalState: "jumping" }), false);
  assert.equal(shouldRestartPlayback({ normalState: "running" }, { normalState: "idle" }), true);
});

test("only a paint for the current operation and frame advances a transition", () => {
  const current = { visualMode: "TRANSITIONING", operationToken: "op-2", frameIndex: 4 };
  assert.equal(isCurrentTransitionPaint(current, { operationToken: "op-2", transitionFrame: 4 }), true);
  assert.equal(isCurrentTransitionPaint(current, { operationToken: "op-1", transitionFrame: 4 }), false);
  assert.equal(isCurrentTransitionPaint(current, { operationToken: "op-2", transitionFrame: 3 }), false);
  assert.equal(isCurrentTransitionPaint({ ...current, visualMode: "NORMAL" },
    { operationToken: "op-2", transitionFrame: 4 }), false);
});
