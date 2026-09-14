import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import {
  cancelTransition,
  completeTransition,
  createRuntimeState,
  isSafePetRelativePath,
  resolvePetRuntime,
  setTargetForm,
  setUnderlyingState,
  validateRuntimeConfig,
} from "./runtime-state.mjs";

const PROJECT_ROOT = fileURLToPath(new URL("../../", import.meta.url));
const FIXTURE_PATH = path.join(PROJECT_ROOT, "runtime-patch/fixtures/liang-runtime.valid.json");
const SCHEMA_PATH = path.join(PROJECT_ROOT, "runtime-patch/schema/liang-runtime.schema.json");

function command(target, requestId = `request-${target}`, animate = true) {
  return { target, animate, requestId };
}

function startTransition(initialForm = "gu") {
  const target = initialForm === "gu" ? "feng" : "gu";
  return setTargetForm(createRuntimeState({ initialForm }), command(target));
}

test("initial gu", () => {
  const state = createRuntimeState({ initialForm: "gu" });
  assert.equal(state.currentForm, "gu");
  assert.equal(state.selectedSource, "forms/gu/spritesheet.webp");
  assert.equal(state.visualState, "NORMAL");
  assert.equal(state.playbackEpoch, 0);
});

test("initial feng", () => {
  const state = createRuntimeState({ initialForm: "feng" });
  assert.equal(state.currentForm, "feng");
  assert.equal(state.selectedSource, "forms/feng/spritesheet.webp");
  assert.equal(state.targetForm, "feng");
});

test("gu to feng transition", () => {
  const { state, response } = startTransition("gu");
  assert.equal(response.accepted, true);
  assert.equal(state.currentForm, "gu");
  assert.equal(state.targetForm, "feng");
  assert.equal(state.transition.name, "gu_to_feng");
  assert.equal(state.visualState, "TRANSITIONING");
});

test("feng to gu transition", () => {
  const { state } = startTransition("feng");
  assert.equal(state.currentForm, "feng");
  assert.equal(state.targetForm, "gu");
  assert.equal(state.transition.name, "feng_to_gu");
});

test("same-form request is a no-op", () => {
  const original = createRuntimeState({ initialForm: "gu" });
  const result = setTargetForm(original, command("gu"));
  assert.strictEqual(result.state, original);
  assert.equal(result.response.noOp, true);
  assert.equal(result.state.playbackEpoch, 0);
});

test("reduced motion commits immediately", () => {
  const original = createRuntimeState({ initialForm: "gu", reducedMotion: true });
  const { state, response } = setTargetForm(original, command("feng"));
  assert.equal(state.currentForm, "feng");
  assert.equal(state.visualState, "NORMAL");
  assert.equal(state.playbackEpoch, 1);
  assert.equal(response.reducedMotion, true);
});

test("missing target atlas rejects without mutation", () => {
  const original = createRuntimeState({
    initialForm: "gu",
    availability: { atlases: { feng: false } },
  });
  const result = setTargetForm(original, command("feng"));
  assert.strictEqual(result.state, original);
  assert.equal(result.response.accepted, false);
  assert.equal(result.response.reason, "target-atlas-unavailable");
});

test("missing transition falls back to an immediate commit", () => {
  const original = createRuntimeState({
    initialForm: "gu",
    availability: { transitions: { gu_to_feng: false } },
  });
  const { state, response } = setTargetForm(original, command("feng"));
  assert.equal(state.currentForm, "feng");
  assert.equal(state.playbackEpoch, 1);
  assert.equal(response.transitionFallback, true);
});

test("valid transition generates an operation token", () => {
  const { state, response } = startTransition("gu");
  assert.match(state.operationToken, /^form-operation-\d+$/);
  assert.equal(response.operationToken, state.operationToken);
});

test("matching operation token completes a transition", () => {
  const started = startTransition("gu");
  const completed = completeTransition(started.state, started.state.operationToken);
  assert.equal(completed.response.completed, true);
  assert.equal(completed.state.currentForm, "feng");
  assert.equal(completed.state.transition, null);
  assert.equal(completed.state.visualState, "NORMAL");
});

test("stale operation token completion is ignored", () => {
  const started = startTransition("gu");
  const result = completeTransition(started.state, "form-operation-stale");
  assert.strictEqual(result.state, started.state);
  assert.equal(result.response.stale, true);
  assert.equal(result.state.currentForm, "gu");
});

test("duplicate same-target request does not restart transition", () => {
  const started = startTransition("gu");
  const duplicate = setTargetForm(started.state, command("feng", "duplicate"));
  assert.strictEqual(duplicate.state, started.state);
  assert.equal(duplicate.response.noOp, true);
  assert.equal(duplicate.response.operationToken, started.state.operationToken);
});

test("reverse request supersedes an active transition deterministically", () => {
  const started = startTransition("gu");
  const oldToken = started.state.operationToken;
  const reversed = setTargetForm(started.state, command("gu", "reverse"));
  assert.equal(reversed.state.currentForm, "gu");
  assert.equal(reversed.state.targetForm, "gu");
  assert.equal(reversed.state.visualState, "NORMAL");
  assert.notEqual(reversed.state.operationToken, oldToken);
  assert.equal(reversed.state.playbackEpoch, 0);
  assert.equal(completeTransition(reversed.state, oldToken).response.stale, true);
});

test("underlying state can change during transition", () => {
  const started = startTransition("gu");
  const updated = setUnderlyingState(started.state, "waiting");
  assert.equal(updated.underlyingState, "waiting");
  assert.equal(updated.visualState, "TRANSITIONING");
  assert.equal(updated.operationToken, started.state.operationToken);
});

test("completion restores the latest underlying state", () => {
  const started = startTransition("gu");
  const updated = setUnderlyingState(started.state, "review");
  const completed = completeTransition(updated, updated.operationToken);
  assert.equal(completed.state.visualState, "NORMAL");
  assert.equal(completed.state.underlyingState, "review");
});

test("playbackEpoch increments only on committed form switches", () => {
  const original = createRuntimeState({ initialForm: "gu" });
  const started = setTargetForm(original, command("feng"));
  assert.equal(started.state.playbackEpoch, 0);
  const completed = completeTransition(started.state, started.state.operationToken);
  assert.equal(completed.state.playbackEpoch, 1);
  const noOp = setTargetForm(completed.state, command("feng", "same"));
  assert.equal(noOp.state.playbackEpoch, 1);
});

test("rejected switch does not increment playbackEpoch", () => {
  const original = createRuntimeState({
    initialForm: "feng",
    availability: { atlases: { gu: false } },
  });
  const rejected = setTargetForm(original, command("gu"));
  assert.equal(rejected.response.accepted, false);
  assert.equal(rejected.state.playbackEpoch, 0);
});

test("cancelled transition cannot later commit", () => {
  const started = startTransition("gu");
  const oldToken = started.state.operationToken;
  const cancelled = cancelTransition(started.state, "overlay-unmounted");
  assert.equal(cancelled.state.visualState, "NORMAL");
  assert.equal(cancelled.state.lastCancelReason, "overlay-unmounted");
  assert.notEqual(cancelled.state.operationToken, oldToken);
  const late = completeTransition(cancelled.state, oldToken);
  assert.equal(late.response.stale, true);
  assert.equal(late.state.currentForm, "gu");
});

test("requestId is preserved across start and completion", () => {
  const requestId = "bridge-request-42";
  const started = setTargetForm(createRuntimeState(), command("feng", requestId));
  assert.equal(started.response.requestId, requestId);
  const completed = completeTransition(started.state, started.state.operationToken);
  assert.equal(completed.response.requestId, requestId);
});

test("invalid form is rejected", () => {
  const original = createRuntimeState();
  const result = setTargetForm(original, command("other"));
  assert.equal(result.response.accepted, false);
  assert.equal(result.response.reason, "invalid-form");
  assert.strictEqual(result.state, original);
});

test("invalid animate type is rejected", () => {
  const original = createRuntimeState();
  const result = setTargetForm(original, command("feng", "bad-animate", "yes"));
  assert.equal(result.response.accepted, false);
  assert.equal(result.response.reason, "invalid-animate");
  assert.strictEqual(result.state, original);
});

test("path contract rejects absolute paths", () => {
  assert.equal(isSafePetRelativePath("/tmp/spritesheet.webp"), false);
  assert.equal(isSafePetRelativePath("C:/pets/spritesheet.webp"), false);
});

test("path contract rejects parent traversal", () => {
  assert.equal(isSafePetRelativePath("../spritesheet.webp"), false);
  assert.equal(isSafePetRelativePath("forms/../spritesheet.webp"), false);
});

test("path contract accepts valid relative paths", () => {
  assert.equal(isSafePetRelativePath("forms/gu/spritesheet.webp"), true);
  assert.equal(isSafePetRelativePath("assets/transform/gu_to_feng/gu_to_feng_01.png"), true);
});

test("sidecar absence preserves native pet behavior", () => {
  const nativePet = Object.freeze({
    id: "custom:ordinary-pet",
    spritesheetPath: "spritesheet.webp",
    spriteVersionNumber: 2,
  });
  const resolved = resolvePetRuntime(nativePet, undefined);
  assert.equal(resolved.mode, "native");
  assert.strictEqual(resolved.pet, nativePet);
  assert.equal(Object.hasOwn(resolved, "runtimeState"), false);
});

test("formal fixture and assets satisfy the frozen contract", () => {
  const schema = JSON.parse(fs.readFileSync(SCHEMA_PATH, "utf8"));
  const fixture = JSON.parse(fs.readFileSync(FIXTURE_PATH, "utf8"));
  assert.equal(schema.$schema, "https://json-schema.org/draft/2020-12/schema");
  assert.equal(schema.properties.schemaVersion.const, 1);
  assert.equal(validateRuntimeConfig(fixture).valid, true);

  for (const form of ["gu", "feng"]) {
    assert.equal(fs.existsSync(path.join(PROJECT_ROOT, fixture.forms[form].spritesheetPath)), true);
  }

  for (const name of ["gu_to_feng", "feng_to_gu"]) {
    const framePaths = fixture.transitions[name].frames;
    const assetDirectory = path.join(PROJECT_ROOT, path.dirname(framePaths[0]));
    const actual = fs.readdirSync(assetDirectory)
      .filter((entry) => entry.endsWith(".png"))
      .sort()
      .map((entry) => path.posix.join(path.posix.dirname(framePaths[0]), entry));
    assert.deepEqual(framePaths, actual);
    for (const frame of framePaths) {
      assert.equal(isSafePetRelativePath(frame), true);
      assert.equal(fs.existsSync(path.join(PROJECT_ROOT, frame)), true);
    }
  }
});
