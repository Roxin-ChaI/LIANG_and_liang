import assert from "node:assert/strict";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { createRuntimeState, setTargetForm } from "../reference/runtime-state.mjs";
import { loadDualFormAvatar } from "./dual-atlas-loader.mjs";
import {
  DualFormSourceError,
  applyCommittedForm,
  createDualFormSourceRegistry,
  selectFormSource,
} from "./dual-form-source.mjs";

const PROJECT_ROOT = fileURLToPath(new URL("../../", import.meta.url));
const FIXTURE = JSON.parse(await fs.readFile(
  path.join(PROJECT_ROOT, "runtime-patch/fixtures/liang-runtime.valid.json"),
  "utf8",
));

function resolvedAvatar() {
  return {
    mode: "dual-form",
    native: { petId: "custom:liang-no-henshin", spriteVersionNumber: 2 },
    forms: {
      gu: {
        spritesheetPath: FIXTURE.forms.gu.spritesheetPath,
        spritesheetDataUrl: "data:image/webp;base64,GU",
        width: 1536,
        height: 2288,
      },
      feng: {
        spritesheetPath: FIXTURE.forms.feng.spritesheetPath,
        spritesheetDataUrl: "data:image/webp;base64,FENG",
        width: 1536,
        height: 2288,
      },
    },
  };
}

function state(initialForm = "gu", underlyingState = "idle") {
  return createRuntimeState({ initialForm, underlyingState, runtimeConfig: FIXTURE });
}

function immediateSwitch(runtimeState, target, requestId = `${runtimeState.currentForm}-to-${target}`) {
  return setTargetForm(runtimeState, { target, animate: false, requestId });
}

function expectSourceCode(callback, code) {
  assert.throws(callback, (error) => error instanceof DualFormSourceError && error.code === code);
}

test("Gu form selects the preloaded Gu source", () => {
  const registry = createDualFormSourceRegistry(resolvedAvatar());
  assert.equal(selectFormSource(registry, "gu"), "data:image/webp;base64,GU");
});

test("Feng form selects the preloaded Feng source", () => {
  const registry = createDualFormSourceRegistry(resolvedAvatar());
  assert.equal(selectFormSource(registry, "feng"), "data:image/webp;base64,FENG");
});

test("source projection preserves the one Pet ID", () => {
  const registry = createDualFormSourceRegistry(resolvedAvatar());
  assert.equal(applyCommittedForm({ runtimeState: state("gu"), registry }).petId, "custom:liang-no-henshin");
  assert.equal(applyCommittedForm({ runtimeState: state("feng"), registry }).petId, "custom:liang-no-henshin");
});

test("gu to feng commit changes source immediately", () => {
  const registry = createDualFormSourceRegistry(resolvedAvatar());
  const switched = immediateSwitch(state("gu"), "feng");
  const selected = applyCommittedForm({ runtimeState: switched.state, registry });
  assert.equal(selected.form, "feng");
  assert.equal(selected.source, "data:image/webp;base64,FENG");
});

test("feng to gu commit changes source immediately", () => {
  const registry = createDualFormSourceRegistry(resolvedAvatar());
  const switched = immediateSwitch(state("feng"), "gu");
  const selected = applyCommittedForm({ runtimeState: switched.state, registry });
  assert.equal(selected.form, "gu");
  assert.equal(selected.source, "data:image/webp;base64,GU");
});

test("multiple committed switches alternate in memory", () => {
  const registry = createDualFormSourceRegistry(resolvedAvatar());
  let runtimeState = state("gu");
  const observed = [];
  for (const target of ["feng", "gu", "feng"]) {
    runtimeState = immediateSwitch(runtimeState, target).state;
    observed.push(applyCommittedForm({ runtimeState, registry }).source);
  }
  assert.deepEqual(observed, [
    "data:image/webp;base64,FENG",
    "data:image/webp;base64,GU",
    "data:image/webp;base64,FENG",
  ]);
});

test("switch projection never calls the loader", () => {
  let loaderCalls = 0;
  const load = () => {
    loaderCalls += 1;
    return resolvedAvatar();
  };
  const registry = createDualFormSourceRegistry(load());
  let runtimeState = state("gu");
  for (const target of ["feng", "gu", "feng"]) {
    runtimeState = immediateSwitch(runtimeState, target).state;
    applyCommittedForm({ runtimeState, registry });
  }
  assert.equal(loaderCalls, 1);
});

test("load once then switch repeatedly performs no disk reread", async (t) => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), "liang-source-switch-"));
  t.after(() => fs.rm(root, { recursive: true, force: true }));
  await fs.writeFile(path.join(root, "pet.json"), JSON.stringify({
    id: "liang-no-henshin",
    displayName: "Liang no Henshin",
    spriteVersionNumber: 2,
    spritesheetPath: "spritesheet.webp",
  }));
  await fs.writeFile(path.join(root, "liang-runtime.json"), JSON.stringify(FIXTURE));
  for (const form of ["gu", "feng"]) {
    const relative = FIXTURE.forms[form].spritesheetPath;
    const destination = path.join(root, relative);
    await fs.mkdir(path.dirname(destination), { recursive: true });
    await fs.copyFile(path.join(PROJECT_ROOT, relative), destination);
  }

  let loaderCalls = 0;
  let atlasReads = 0;
  const load = async () => {
    loaderCalls += 1;
    return loadDualFormAvatar({
      petRoot: root,
      io: {
        readFile: async (...args) => {
          if (String(args[0]).endsWith(".webp")) atlasReads += 1;
          return fs.readFile(...args);
        },
      },
    });
  };
  const registry = createDualFormSourceRegistry(await load());
  assert.equal(loaderCalls, 1);
  assert.equal(atlasReads, 2);

  let runtimeState = state("gu");
  for (const target of ["feng", "gu", "feng"]) {
    runtimeState = immediateSwitch(runtimeState, target).state;
    applyCommittedForm({ runtimeState, registry });
  }
  assert.equal(loaderCalls, 1);
  assert.equal(atlasReads, 2);
});

test("form source and playbackEpoch derive from one committed state", () => {
  const registry = createDualFormSourceRegistry(resolvedAvatar());
  const before = applyCommittedForm({ runtimeState: state("gu"), registry });
  const switched = immediateSwitch(state("gu"), "feng");
  const after = applyCommittedForm({ runtimeState: switched.state, registry });
  assert.deepEqual(
    [before.form, before.source, before.playbackEpoch],
    ["gu", "data:image/webp;base64,GU", 0],
  );
  assert.deepEqual(
    [after.form, after.source, after.playbackEpoch],
    ["feng", "data:image/webp;base64,FENG", 1],
  );
});

test("same-form request preserves source identity and playbackEpoch", () => {
  const registry = createDualFormSourceRegistry(resolvedAvatar());
  const original = state("gu");
  const before = applyCommittedForm({ runtimeState: original, registry });
  const noOp = immediateSwitch(original, "gu");
  const after = applyCommittedForm({ runtimeState: noOp.state, registry });
  assert.strictEqual(noOp.state, original);
  assert.strictEqual(after.source, before.source);
  assert.equal(after.playbackEpoch, before.playbackEpoch);
});

test("underlying task state survives form switch", () => {
  const registry = createDualFormSourceRegistry(resolvedAvatar());
  const switched = immediateSwitch(state("gu", "running"), "feng");
  const selected = applyCommittedForm({ runtimeState: switched.state, registry });
  assert.equal(selected.underlyingState, "running");
});

test("invalid form is rejected", () => {
  const registry = createDualFormSourceRegistry(resolvedAvatar());
  expectSourceCode(() => selectFormSource(registry, "other"), "INVALID_FORM");
});

test("missing form source is rejected", () => {
  const avatar = resolvedAvatar();
  delete avatar.forms.feng;
  expectSourceCode(() => createDualFormSourceRegistry(avatar), "MISSING_FORM_SOURCE");
});
