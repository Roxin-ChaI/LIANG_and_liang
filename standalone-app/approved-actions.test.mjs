import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { frameAt, APPROVED_FORM_DURATIONS } from "./animation.mjs";
import { rendererHarness, transitionState } from "./test-support/renderer-harness.mjs";

const manifest = JSON.parse(fs.readFileSync(new URL("../assets/rework/v0.1.0/approved-actions-integration-2026-10-23/manifest.json", import.meta.url)));

test("every integrated state matches approved GIF frame boundaries and wrap", () => {
  for (const row of manifest.replacements) {
    let time = 0;
    for (let i=0; i<row.frames; i++) {
      assert.equal(frameAt(row.state, time, {form: row.form}).frame, i);
      assert.equal(frameAt(row.state, time + row.durationsMs[i]-1, {form: row.form}).frame, i);
      time += row.durationsMs[i];
    }
    assert.equal(frameAt(row.state, time, {form: row.form}).frame, 0);
    if (!["running-left", "running-right"].includes(row.state)) {
      assert.equal(frameAt(row.state, time*3, {form: row.form}).state, "idle");
    }
  }
});

test("Feng timing cannot leak into Gu, work Running, Look or Idle", () => {
  assert.equal(frameAt("running-right", 120, {form:"gu"}).frame, 1);
  assert.equal(frameAt("running-right", 120, {form:"feng"}).frame, 0);
  for (const state of ["idle", "running", "waiting", "jumping", "look-row-9", "look-row-10"]) {
    for (const time of [0, 140, 1000, 9000]) {
      assert.deepEqual(frameAt(state,time,{form:"feng"}), frameAt(state,time,{form:"gu"}));
    }
  }
  assert.ok(Object.isFrozen(APPROVED_FORM_DURATIONS.feng.failed));
});

test("actual renderer supplies active form to timing selection", async () => {
  const calls=[];
  const h=rendererHarness({libraries:{frameAt:(state,elapsed,options)=>{
    calls.push(options.form); return frameAt(state,elapsed,options);
  }}});
  await h.receive(transitionState({currentForm:"feng", normalSource:"feng-atlas",
    normalState:"running-right", visualMode:"NORMAL", frameIndex:null, transitionId:null, overlayImage:null}));
  h.paint(0); h.paint(1); h.paint(120);
  assert.ok(calls.includes("feng"));
  assert.equal(h.errors.length,0);
});
