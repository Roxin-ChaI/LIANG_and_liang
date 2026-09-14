import assert from "node:assert/strict";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import {
  DualAtlasLoadError,
  loadDualFormAvatar,
  parseWebPDimensions,
} from "./dual-atlas-loader.mjs";

const PROJECT_ROOT = fileURLToPath(new URL("../../", import.meta.url));
const GU_ATLAS = path.join(PROJECT_ROOT, "assets/builds/gu/spritesheet.webp");
const FENG_ATLAS = path.join(PROJECT_ROOT, "assets/builds/feng/spritesheet.webp");
const FIXTURE = JSON.parse(await fs.readFile(
  path.join(PROJECT_ROOT, "runtime-patch/fixtures/liang-runtime.valid.json"),
  "utf8",
));

const NATIVE_MANIFEST = Object.freeze({
  id: "liang-no-henshin",
  displayName: "Liang no Henshin",
  spriteVersionNumber: 2,
  spritesheetPath: "spritesheet.webp",
});

async function makePetRoot(t, { sidecar = FIXTURE, copyGu = true, copyFeng = true } = {}) {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), "liang-dual-atlas-"));
  t.after(() => fs.rm(root, { recursive: true, force: true }));
  await fs.writeFile(path.join(root, "pet.json"), `${JSON.stringify(NATIVE_MANIFEST, null, 2)}\n`);
  if (sidecar !== null) {
    await fs.writeFile(path.join(root, "liang-runtime.json"), `${JSON.stringify(sidecar, null, 2)}\n`);
  }
  if (copyGu) {
    const target = path.join(root, FIXTURE.forms.gu.spritesheetPath);
    await fs.mkdir(path.dirname(target), { recursive: true });
    await fs.copyFile(GU_ATLAS, target);
  }
  if (copyFeng) {
    const target = path.join(root, FIXTURE.forms.feng.spritesheetPath);
    await fs.mkdir(path.dirname(target), { recursive: true });
    await fs.copyFile(FENG_ATLAS, target);
  }
  return root;
}

function cloneFixture() {
  return structuredClone(FIXTURE);
}

async function expectCode(promise, code) {
  await assert.rejects(promise, (error) => error instanceof DualAtlasLoadError && error.code === code);
}

test("sidecar absent returns native-only without loading an atlas", async (t) => {
  const root = await makePetRoot(t, { sidecar: null, copyGu: false, copyFeng: false });
  let atlasReads = 0;
  const resolved = await loadDualFormAvatar({
    petRoot: root,
    io: {
      readFile: async (...args) => {
        if (String(args[0]).endsWith(".webp")) atlasReads += 1;
        return fs.readFile(...args);
      },
    },
  });
  assert.equal(resolved.mode, "native-only");
  assert.equal(resolved.native.petId, "custom:liang-no-henshin");
  assert.equal(atlasReads, 0);
});

test("valid sidecar loads gu and feng exactly once", async (t) => {
  const root = await makePetRoot(t);
  const counts = { gu: 0, feng: 0 };
  const resolved = await loadDualFormAvatar({
    petRoot: root,
    io: {
      readFile: async (...args) => {
        const filePath = String(args[0]);
        if (filePath.endsWith("spritesheet.webp") && filePath.includes("/gu/")) counts.gu += 1;
        if (filePath.endsWith("spritesheet.webp") && filePath.includes("/feng/")) counts.feng += 1;
        return fs.readFile(...args);
      },
    },
  });
  assert.equal(resolved.mode, "dual-form");
  assert.deepEqual(counts, { gu: 1, feng: 1 });
});

test("both formal atlases report v2 dimensions", async (t) => {
  const root = await makePetRoot(t);
  const resolved = await loadDualFormAvatar({ petRoot: root });
  assert.deepEqual(
    [resolved.forms.gu.width, resolved.forms.gu.height, resolved.forms.feng.width, resolved.forms.feng.height],
    [1536, 2288, 1536, 2288],
  );
});

test("malformed sidecar fails explicitly", async (t) => {
  const root = await makePetRoot(t, { sidecar: null });
  await fs.writeFile(path.join(root, "liang-runtime.json"), "{broken");
  await expectCode(loadDualFormAvatar({ petRoot: root }), "MALFORMED_SIDECAR");
});

test("missing gu form fails schema validation", async (t) => {
  const sidecar = cloneFixture();
  delete sidecar.forms.gu;
  const root = await makePetRoot(t, { sidecar });
  await expectCode(loadDualFormAvatar({ petRoot: root }), "INVALID_SIDECAR");
});

test("missing feng form fails schema validation", async (t) => {
  const sidecar = cloneFixture();
  delete sidecar.forms.feng;
  const root = await makePetRoot(t, { sidecar });
  await expectCode(loadDualFormAvatar({ petRoot: root }), "INVALID_SIDECAR");
});

test("missing atlas fails explicitly", async (t) => {
  const root = await makePetRoot(t, { copyFeng: false });
  await expectCode(loadDualFormAvatar({ petRoot: root }), "ASSET_MISSING");
});

test("invalid atlas dimensions fail explicitly", async (t) => {
  const root = await makePetRoot(t);
  const target = path.join(root, FIXTURE.forms.feng.spritesheetPath);
  const invalid = Buffer.from(await fs.readFile(FENG_ATLAS));
  const bits = invalid.readUInt32LE(21);
  invalid.writeUInt32LE((bits & ~0x3fff) | 99, 21);
  await fs.writeFile(target, invalid);
  await expectCode(loadDualFormAvatar({ petRoot: root }), "INVALID_ATLAS_DIMENSIONS");
});

test("absolute atlas path is rejected", async (t) => {
  const sidecar = cloneFixture();
  sidecar.forms.gu.spritesheetPath = GU_ATLAS;
  const root = await makePetRoot(t, { sidecar });
  await expectCode(loadDualFormAvatar({ petRoot: root }), "INVALID_SIDECAR");
});

test("parent traversal is rejected", async (t) => {
  const sidecar = cloneFixture();
  sidecar.forms.feng.spritesheetPath = "../spritesheet.webp";
  const root = await makePetRoot(t, { sidecar });
  await expectCode(loadDualFormAvatar({ petRoot: root }), "INVALID_SIDECAR");
});

test("symlink escape is rejected after realpath", async (t) => {
  const root = await makePetRoot(t, { copyFeng: false });
  const outside = await fs.mkdtemp(path.join(os.tmpdir(), "liang-outside-"));
  t.after(() => fs.rm(outside, { recursive: true, force: true }));
  const outsideAtlas = path.join(outside, "spritesheet.webp");
  await fs.copyFile(FENG_ATLAS, outsideAtlas);
  const target = path.join(root, FIXTURE.forms.feng.spritesheetPath);
  await fs.mkdir(path.dirname(target), { recursive: true });
  await fs.symlink(outsideAtlas, target);
  await expectCode(loadDualFormAvatar({ petRoot: root }), "PATH_ESCAPE");
});

test("loaded atlases produce WebP data URLs", async (t) => {
  const root = await makePetRoot(t);
  const resolved = await loadDualFormAvatar({ petRoot: root });
  assert.match(resolved.forms.gu.spritesheetDataUrl, /^data:image\/webp;base64,UklGR/);
  assert.match(resolved.forms.feng.spritesheetDataUrl, /^data:image\/webp;base64,UklGR/);
});

test("native manifest input remains unchanged", async (t) => {
  const root = await makePetRoot(t);
  const manifest = structuredClone(NATIVE_MANIFEST);
  const before = JSON.stringify(manifest);
  await loadDualFormAvatar({ petRoot: root, nativeManifest: manifest });
  assert.equal(JSON.stringify(manifest), before);
  assert.equal(Object.hasOwn(manifest, "petId"), false);
});

test("formal Gu and Feng files parse as lossless WebP v2 atlases", async () => {
  assert.deepEqual(parseWebPDimensions(await fs.readFile(GU_ATLAS)), { width: 1536, height: 2288 });
  assert.deepEqual(parseWebPDimensions(await fs.readFile(FENG_ATLAS)), { width: 1536, height: 2288 });
});
