import assert from "node:assert/strict";
import test from "node:test";
import { createDualFormSourceRegistry } from "../prototype/dual-form-source.mjs";
import { loadTransitionAssets } from "../prototype/transition-assets.mjs";
import { createTransitionPlayer } from "../prototype/transition-player.mjs";
import { createRuntimeDispatch } from "./runtime-dispatch.mjs";

const assets = await loadTransitionAssets();
function player(options = {}) {
  const registry = createDualFormSourceRegistry({
    mode: "dual-form", native: { petId: "custom:liang-no-henshin" },
    forms: {
      gu: { spritesheetPath: "assets/builds/gu/spritesheet.webp", spritesheetDataUrl: "data:image/webp;base64,GU" },
      feng: { spritesheetPath: "assets/builds/feng/spritesheet.webp", spritesheetDataUrl: "data:image/webp;base64,FENG" },
    },
  });
  return createTransitionPlayer({ registry, assets, ...options });
}
const invoke = (dispatch, target, animate = true, requestId = `request-${target}`) =>
  dispatch({ requestId, target, animate });

test("bridge dispatch accepts Gu", async () => {
  const runtime = player({ initialForm: "feng" }); const result = await invoke(createRuntimeDispatch(runtime), "gu");
  assert.deepEqual([result.accepted, result.currentForm, result.targetForm], [true, "feng", "gu"]);
});
test("bridge dispatch accepts Feng", async () => {
  const runtime = player(); const result = await invoke(createRuntimeDispatch(runtime), "feng");
  assert.deepEqual([result.accepted, result.currentForm, result.targetForm], [true, "gu", "feng"]);
});
test("animated request starts transition", async () => {
  const runtime = player(); const result = await invoke(createRuntimeDispatch(runtime), "feng", true);
  assert.equal(result.transitioning, true);
});
test("non-animated request commits immediately", async () => {
  const runtime = player(); const result = await invoke(createRuntimeDispatch(runtime), "feng", false);
  assert.deepEqual([result.transitioning, result.currentForm, runtime.snapshot().playbackEpoch], [false, "feng", 1]);
});
test("same target is an accepted no-op", async () => {
  const runtime = player(); const before = runtime.snapshot(); const result = await invoke(createRuntimeDispatch(runtime), "gu");
  assert.deepEqual([result.accepted, result.transitioning, runtime.snapshot().playbackEpoch], [true, false, before.playbackEpoch]);
});
test("duplicate active target does not restart operation", async () => {
  const runtime = player(); const dispatch = createRuntimeDispatch(runtime); await invoke(dispatch, "feng", true, "first");
  runtime.advance(280); const before = runtime.snapshot(); await invoke(dispatch, "feng", true, "duplicate");
  assert.deepEqual([runtime.snapshot().operationToken, runtime.snapshot().frameIndex], [before.operationToken, before.frameIndex]);
});
test("reverse request cancels active operation", async () => {
  const runtime = player(); const dispatch = createRuntimeDispatch(runtime); await invoke(dispatch, "feng", true, "forward");
  const token = runtime.snapshot().operationToken; const result = await invoke(dispatch, "gu", true, "reverse");
  assert.deepEqual([result.currentForm, result.targetForm, result.transitioning], ["gu", "gu", false]);
  assert.notEqual(runtime.snapshot().operationToken, token);
});
test("stale-token completion remains ineffective through adapter", async () => {
  const runtime = player(); const dispatch = createRuntimeDispatch(runtime); await invoke(dispatch, "feng", true, "forward");
  const token = runtime.snapshot().operationToken; await invoke(dispatch, "gu", true, "reverse");
  assert.equal(runtime.complete(token).stale, true); assert.equal(runtime.snapshot().currentForm, "gu");
});
test("reduced motion still commits immediately", async () => {
  const runtime = player({ reducedMotion: true }); const result = await invoke(createRuntimeDispatch(runtime), "feng");
  assert.deepEqual([result.currentForm, result.transitioning, runtime.snapshot().playbackEpoch], ["feng", false, 1]);
});
test("requestId is correlated unchanged", async () => {
  const runtime = player(); const result = await invoke(createRuntimeDispatch(runtime), "feng", true, "correlation-123");
  assert.equal(result.requestId, "correlation-123");
});
test("adapter does not expose a second state machine", () => {
  const runtime = player(); const dispatch = createRuntimeDispatch(runtime);
  assert.equal(typeof dispatch, "function"); assert.deepEqual(Object.keys(dispatch), []);
});
