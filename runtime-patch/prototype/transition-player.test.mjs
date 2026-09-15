import assert from "node:assert/strict";
import fs from "node:fs/promises";
import test from "node:test";
import { createDualFormSourceRegistry } from "./dual-form-source.mjs";
import { loadTransitionAssets } from "./transition-assets.mjs";
import { createTransitionPlayer } from "./transition-player.mjs";

const ASSETS = await loadTransitionAssets();
const DURATION = 140;

function registry() {
  return createDualFormSourceRegistry({
    mode: "dual-form", native: { petId: "custom:liang-no-henshin" },
    forms: {
      gu: { spritesheetPath: "assets/builds/gu/spritesheet.webp", spritesheetDataUrl: "data:image/webp;base64,GU" },
      feng: { spritesheetPath: "assets/builds/feng/spritesheet.webp", spritesheetDataUrl: "data:image/webp;base64,FENG" },
    },
  });
}
function player(options = {}) { return createTransitionPlayer({ registry: registry(), assets: ASSETS, ...options }); }
function begin(p, target) { return p.requestTargetForm(target, { requestId: `test-${target}` }); }

test("Gu normal uses preloaded Gu atlas", () => {
  const visual = player().snapshot();
  assert.deepEqual([visual.visualMode, visual.currentForm, visual.normalSource], ["NORMAL", "gu", "data:image/webp;base64,GU"]);
});
test("Feng normal uses preloaded Feng atlas", () => {
  const visual = player({ initialForm: "feng" }).snapshot();
  assert.deepEqual([visual.visualMode, visual.currentForm, visual.normalSource], ["NORMAL", "feng", "data:image/webp;base64,FENG"]);
});
test("Gu→Feng visits exactly ten ordered oversized frames", () => {
  const p = player(); begin(p, "feng");
  for (let index = 0; index < 10; index += 1) {
    assert.equal(p.snapshot().frameIndex, index);
    assert.equal(p.snapshot().frameSource, `assets/transform-overlay/gu_to_feng/gu_to_feng_${String(index + 1).padStart(2, "0")}.png`);
    p.advance(DURATION);
  }
  assert.deepEqual([p.snapshot().visualMode, p.snapshot().currentForm], ["NORMAL", "feng"]);
});
test("Feng→Gu visits exactly eight ordered oversized frames", () => {
  const p = player({ initialForm: "feng" }); begin(p, "gu");
  for (let index = 0; index < 8; index += 1) { assert.equal(p.snapshot().frameIndex, index); p.advance(DURATION); }
  assert.deepEqual([p.snapshot().visualMode, p.snapshot().currentForm], ["NORMAL", "gu"]);
});
test("frame zero occupies its complete duration", () => {
  const p = player(); begin(p, "feng"); p.advance(DURATION - 1);
  assert.equal(p.snapshot().frameIndex, 0);
  p.advance(1); assert.equal(p.snapshot().frameIndex, 1);
});
test("last frame occupies its complete duration and early completion is refused", () => {
  const p = player(); const token = begin(p, "feng").operationToken;
  p.advance(10 * DURATION - 1);
  assert.equal(p.snapshot().frameIndex, 9);
  assert.equal(p.complete(token).reason, "last-frame-incomplete");
  assert.equal(p.snapshot().currentForm, "gu");
  p.advance(1); assert.equal(p.snapshot().currentForm, "feng");
});
test("completion atomically commits target source, form and normal mode", () => {
  const p = player(); begin(p, "feng"); p.advance(10 * DURATION);
  assert.deepEqual([p.snapshot().currentForm, p.snapshot().targetForm, p.snapshot().normalSource, p.snapshot().visualMode],
    ["feng", "feng", "data:image/webp;base64,FENG", "NORMAL"]);
});
test("playbackEpoch changes only at form commit", () => {
  const p = player(); begin(p, "feng"); p.advance(9 * DURATION);
  assert.equal(p.snapshot().playbackEpoch, 0);
  p.advance(DURATION); assert.equal(p.snapshot().playbackEpoch, 1);
});
test("duplicate active target keeps operation token and progress", () => {
  const p = player(); begin(p, "feng"); p.advance(3 * DURATION);
  const before = p.snapshot(); const response = begin(p, "feng");
  assert.equal(response.noOp, true);
  assert.deepEqual([p.snapshot().frameIndex, p.snapshot().operationToken, p.snapshot().playbackEpoch],
    [before.frameIndex, before.operationToken, before.playbackEpoch]);
});
test("reverse request cancels old operation without changing Gu or epoch", () => {
  const p = player(); const old = begin(p, "feng").operationToken; p.advance(2 * DURATION);
  const response = begin(p, "gu");
  assert.equal(response.cancelled, true);
  assert.deepEqual([p.snapshot().visualMode, p.snapshot().currentForm, p.snapshot().playbackEpoch], ["NORMAL", "gu", 0]);
  assert.notEqual(p.snapshot().operationToken, old);
});
test("Feng→Gu→Feng reverse also preserves Feng", () => {
  const p = player({ initialForm: "feng" }); begin(p, "gu"); p.advance(200); begin(p, "feng");
  assert.deepEqual([p.snapshot().visualMode, p.snapshot().currentForm, p.snapshot().playbackEpoch], ["NORMAL", "feng", 0]);
});
test("stale completion token is ignored after reversal and subsequent request", () => {
  const p = player(); const old = begin(p, "feng").operationToken;
  begin(p, "gu"); begin(p, "feng"); p.advance(10 * DURATION - 1);
  assert.equal(p.complete(old).stale, true);
  assert.equal(p.snapshot().currentForm, "gu");
});
test("completion cannot commit twice", () => {
  const p = player(); const token = begin(p, "feng").operationToken; p.advance(10 * DURATION);
  assert.equal(p.complete(token).stale, true);
  assert.equal(p.snapshot().playbackEpoch, 1);
});
test("hover cannot alter transition visual", () => {
  const p = player(); begin(p, "feng"); const frame = p.snapshot().frameSource;
  p.updateInteraction("hover", true);
  assert.deepEqual([p.snapshot().visualMode, p.snapshot().frameSource], ["TRANSITIONING", frame]);
});
test("drag cannot alter transition visual or hitbox-owned playback", () => {
  const p = player(); begin(p, "feng"); const frame = p.snapshot().frameSource;
  p.updateInteraction("drag", "running-right");
  assert.deepEqual([p.snapshot().visualMode, p.snapshot().frameSource], ["TRANSITIONING", frame]);
});
test("look cannot alter transition visual", () => {
  const p = player(); begin(p, "feng"); const frame = p.snapshot().frameSource;
  p.updateInteraction("look", 5);
  assert.deepEqual([p.snapshot().visualMode, p.snapshot().frameSource], ["TRANSITIONING", frame]);
});
test("underlying task state can update and resumes on the target form", () => {
  const p = player(); begin(p, "feng"); p.updateUnderlyingState("running");
  assert.equal(p.snapshot().visualMode, "TRANSITIONING");
  p.advance(10 * DURATION);
  assert.deepEqual([p.snapshot().currentForm, p.snapshot().normalState], ["feng", "running"]);
});
test("reduced motion commits immediately without transition visual", () => {
  const p = player({ reducedMotion: true }); begin(p, "feng");
  assert.deepEqual([p.snapshot().visualMode, p.snapshot().currentForm, p.snapshot().playbackEpoch], ["NORMAL", "feng", 1]);
});
test("missing/invalid oversized assets trigger immediate fallback", () => {
  const p = player({ assets: { ...ASSETS, gu_to_feng: null } }); begin(p, "feng");
  assert.deepEqual([p.snapshot().transitionFallback, p.snapshot().currentForm, p.snapshot().playbackEpoch], [true, "feng", 1]);
});
test("invalid target atlas is rejected without modifying playback", () => {
  const p = player({ availability: { atlases: { feng: false } } });
  const response = begin(p, "feng");
  assert.deepEqual([response.accepted, p.snapshot().currentForm, p.snapshot().playbackEpoch], [false, "gu", 0]);
});
test("one Pet ID is unchanged before, during and after transition", () => {
  const p = player(); const id = p.snapshot().petId; begin(p, "feng");
  assert.equal(p.snapshot().petId, id); p.advance(10 * DURATION); assert.equal(p.snapshot().petId, id);
});
test("asset and atlas source registries are read once, never by advance/request", async () => {
  let reads = 0;
  const loaded = await loadTransitionAssets({ readFile: async (file) => { reads += 1; return fs.readFile(file); } });
  const count = reads;
  const p = player({ assets: loaded }); begin(p, "feng"); p.advance(10 * DURATION); begin(p, "gu"); p.advance(8 * DURATION);
  assert.equal(reads, count);
});
test("every transition frame carries the frozen overlay layout", () => {
  const p = player(); begin(p, "feng"); const layout = p.snapshot().overlayLayout;
  for (let index = 0; index < 10; index += 1) { assert.strictEqual(p.snapshot().overlayLayout, layout); p.advance(DURATION); }
});
test("bulk advance does not skip last-frame duration", () => {
  const p = player(); begin(p, "feng"); p.advance(10 * DURATION - 1);
  assert.equal(p.snapshot().frameIndex, 9);
  p.advance(1); assert.equal(p.snapshot().currentForm, "feng");
});
