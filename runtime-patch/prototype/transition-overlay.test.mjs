import assert from "node:assert/strict";
import test from "node:test";
import { createDualFormSourceRegistry } from "./dual-form-source.mjs";
import { loadTransitionAssets } from "./transition-assets.mjs";
import { renderTransitionOverlay } from "./transition-overlay.mjs";
import { createTransitionPlayer } from "./transition-player.mjs";

const ASSETS = await loadTransitionAssets();
function player(initialForm = "gu") {
  const registry = createDualFormSourceRegistry({
    mode: "dual-form", native: { petId: "custom:liang-no-henshin" },
    forms: {
      gu: { spritesheetPath: "assets/builds/gu/spritesheet.webp", spritesheetDataUrl: "data:image/webp;base64,GU" },
      feng: { spritesheetPath: "assets/builds/feng/spritesheet.webp", spritesheetDataUrl: "data:image/webp;base64,FENG" },
    },
  });
  return createTransitionPlayer({ registry, assets: ASSETS, initialForm });
}
function start(form = "gu") { const p = player(form); p.requestTargetForm(form === "gu" ? "feng" : "gu"); return p; }

test("normal box is fixed at 192×208", () => {
  const plan = renderTransitionOverlay(player().snapshot());
  assert.deepEqual([plan.width, plan.height, plan.normal.width, plan.normal.height], [192, 208, 192, 208]);
});
test("Gu→Feng overlay canvas is 224×240", () => {
  const plan = renderTransitionOverlay(start().snapshot());
  assert.deepEqual([plan.overlay.width, plan.overlay.height], [224, 240]);
});
test("Feng→Gu overlay canvas is 208×224", () => {
  const plan = renderTransitionOverlay(start("feng").snapshot());
  assert.deepEqual([plan.overlay.width, plan.overlay.height], [208, 224]);
});
test("overlay anchor maps to normal x=96", () => {
  for (const form of ["gu", "feng"]) {
    const plan = renderTransitionOverlay(start(form).snapshot());
    assert.equal(plan.overlay.left + plan.overlay.anchor.x, 96);
  }
});
test("overlay baseline maps to normal y=203", () => {
  for (const form of ["gu", "feng"]) {
    const plan = renderTransitionOverlay(start(form).snapshot());
    assert.equal(plan.overlay.top + plan.overlay.anchor.y, 203);
  }
});
test("oversized overlay may have negative left", () => {
  assert.equal(renderTransitionOverlay(start().snapshot()).overlay.left, -16);
  assert.equal(renderTransitionOverlay(start("feng").snapshot()).overlay.left, -9);
});
test("oversized overlay may have negative top", () => {
  assert.equal(renderTransitionOverlay(start().snapshot()).overlay.top, -18);
  assert.equal(renderTransitionOverlay(start("feng").snapshot()).overlay.top, -14);
});
test("transition layer is absolute and pointer-events none", () => {
  const overlay = renderTransitionOverlay(start().snapshot()).overlay;
  assert.deepEqual([overlay.style.position, overlay.style.pointerEvents], ["absolute", "none"]);
});
test("normal marked hitbox is unchanged throughout playback", () => {
  const p = start(); const before = renderTransitionOverlay(p.snapshot()).normal.hitbox;
  p.advance(5 * 140); const after = renderTransitionOverlay(p.snapshot()).normal.hitbox;
  assert.deepEqual(after, before);
  assert.deepEqual(after, { left: 0, top: 0, width: 192, height: 208, region: "mascot" });
});
test("normal position and drag coordinates do not move", () => {
  const p = start(); const first = renderTransitionOverlay(p.snapshot()).normal;
  p.advance(6 * 140); const next = renderTransitionOverlay(p.snapshot()).normal;
  assert.deepEqual([first.left, first.top, next.left, next.top], [0, 0, 0, 0]);
  assert.deepEqual(first.dragCoordinates, next.dragCoordinates);
});
test("overlay is removed after one-shot completion", () => {
  const p = start(); p.advance(10 * 140);
  const plan = renderTransitionOverlay(p.snapshot());
  assert.equal(plan.overlay, null);
  assert.equal(plan.layoutWrapper.children.length, 1);
});
test("target form's preloaded source takes over the normal renderer", () => {
  const p = start(); p.advance(10 * 140);
  const normal = renderTransitionOverlay(p.snapshot()).normal;
  assert.deepEqual([normal.form, normal.source, normal.playbackEpoch], ["feng", "data:image/webp;base64,FENG", 1]);
});
test("renderer never performs source reread", () => {
  const p = start();
  for (let index = 0; index < 10; index += 1) { renderTransitionOverlay(p.snapshot()); p.advance(140); }
  assert.equal(renderTransitionOverlay(p.snapshot()).normal.source, "data:image/webp;base64,FENG");
});
test("Pet ID stays the same across sibling and normal renderer", () => {
  const plan = renderTransitionOverlay(start().snapshot());
  assert.equal(plan.petId, plan.normal.petId);
  assert.equal(plan.petId, "custom:liang-no-henshin");
});
test("every Gu→Feng frame uses identical overlay geometry", () => {
  const p = start(); const geometry = [];
  for (let index = 0; index < 10; index += 1) {
    const o = renderTransitionOverlay(p.snapshot()).overlay;
    geometry.push([o.left, o.top, o.width, o.height]); p.advance(140);
  }
  assert.equal(new Set(geometry.map(JSON.stringify)).size, 1);
});
test("every Feng→Gu frame uses identical overlay geometry", () => {
  const p = start("feng"); const geometry = [];
  for (let index = 0; index < 8; index += 1) {
    const o = renderTransitionOverlay(p.snapshot()).overlay;
    geometry.push([o.left, o.top, o.width, o.height]); p.advance(140);
  }
  assert.equal(new Set(geometry.map(JSON.stringify)).size, 1);
});
test("sibling is outside normal clipped root, without expanding it", () => {
  const plan = renderTransitionOverlay(start().snapshot());
  assert.equal(plan.normal.clip, "overflow-hidden");
  assert.equal(plan.overlay.clipPolicy, "outside-normal-clipped-root");
  assert.deepEqual(plan.layoutWrapper.children.map((child) => child.type), ["NormalPetRenderer", "TransitionOverlay"]);
});
