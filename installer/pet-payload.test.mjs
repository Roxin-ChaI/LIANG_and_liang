import assert from "node:assert/strict";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test, { after, before } from "node:test";

import {
  MANIFEST_NAME,
  PET_ID,
  PROJECT_ROOT,
  buildPetPayload,
  isSafeRelativePath,
  sha256File,
  validatePayload,
} from "./pet-payload.mjs";

let root;
let first;
let second;
let sourceHashes;

async function sourceSnapshot() {
  const paths = [
    "assets/builds/gu/spritesheet.webp",
    "assets/builds/feng/spritesheet.webp",
    ...Array.from({ length: 10 }, (_, index) => `assets/transform-overlay/gu_to_feng/gu_to_feng_${String(index + 1).padStart(2, "0")}.png`),
    ...Array.from({ length: 8 }, (_, index) => `assets/transform-overlay/feng_to_gu/feng_to_gu_${String(index + 1).padStart(2, "0")}.png`),
  ];
  return Object.fromEntries(await Promise.all(paths.map(async relative => [relative, await sha256File(path.join(PROJECT_ROOT, relative))])));
}

before(async () => {
  root = await fs.mkdtemp(path.join(os.tmpdir(), "liang-payload-test-"));
  sourceHashes = await sourceSnapshot();
  first = await buildPetPayload({ outputRoot: path.join(root, "first") });
  second = await buildPetPayload({ outputRoot: path.join(root, "second") });
});

after(async () => {
  await fs.rm(root, { recursive: true, force: true });
});

test("payload layout is complete", async () => {
  for (const relative of [
    "pet.json", "spritesheet.webp", "liang-runtime.json", MANIFEST_NAME,
    "forms/gu/spritesheet.webp", "forms/feng/spritesheet.webp",
    "transitions/gu_to_feng/gu_to_feng_01.png",
    "transitions/feng_to_gu/feng_to_gu_01.png",
  ]) assert.equal((await fs.stat(path.join(first.petRoot, relative))).isFile(), true);
});

test("native manifest preserves one Pet identity", async () => {
  const pet = JSON.parse(await fs.readFile(path.join(first.petRoot, "pet.json")));
  assert.deepEqual(pet, {
    id: "liang-no-henshin",
    displayName: "Liang no Henshin",
    description: "Single-ID Codex Pet with Gu fallback and patched dual-form runtime metadata.",
    spriteVersionNumber: 2,
    spritesheetPath: "spritesheet.webp",
  });
});

test("native fallback is byte-identical to formal Gu", async () => {
  assert.equal(await sha256File(path.join(first.petRoot, "spritesheet.webp")), await sha256File(path.join(PROJECT_ROOT, "assets/builds/gu/spritesheet.webp")));
});

test("form atlases are byte-identical to formal sources", async () => {
  assert.equal(await sha256File(path.join(first.petRoot, "forms/gu/spritesheet.webp")), sourceHashes["assets/builds/gu/spritesheet.webp"]);
  assert.equal(await sha256File(path.join(first.petRoot, "forms/feng/spritesheet.webp")), sourceHashes["assets/builds/feng/spritesheet.webp"]);
});

test("transition counts and ordered names are frozen", async () => {
  const sidecar = JSON.parse(await fs.readFile(path.join(first.petRoot, "liang-runtime.json")));
  assert.equal(sidecar.transitions.gu_to_feng.frames.length, 10);
  assert.equal(sidecar.transitions.feng_to_gu.frames.length, 8);
  assert.equal(sidecar.transitions.gu_to_feng.frames.at(0), "transitions/gu_to_feng/gu_to_feng_01.png");
  assert.equal(sidecar.transitions.gu_to_feng.frames.at(-1), "transitions/gu_to_feng/gu_to_feng_10.png");
  assert.equal(sidecar.transitions.feng_to_gu.frames.at(-1), "transitions/feng_to_gu/feng_to_gu_08.png");
});

test("sidecar schema and initial form are production values", async () => {
  const sidecar = JSON.parse(await fs.readFile(path.join(first.petRoot, "liang-runtime.json")));
  assert.equal(sidecar.schemaVersion, 1);
  assert.equal(sidecar.initialForm, "gu");
  assert.equal(sidecar.forms.gu.spritesheetPath, "forms/gu/spritesheet.webp");
});

test("overlay metadata is consistent with every actual RGBA PNG", async () => {
  const result = await validatePayload(first.petRoot);
  assert.equal(result.ok, true);
  assert.deepEqual(result.sidecar.transitions.gu_to_feng.layout, {
    anchorX: 112, anchorY: 221, canvasHeight: 240, canvasWidth: 224,
    offsetLeft: -16, offsetTop: -18, petAnchorX: 96, petBaselineY: 203,
  });
  assert.deepEqual(result.sidecar.transitions.feng_to_gu.layout, {
    anchorX: 105, anchorY: 217, canvasHeight: 224, canvasWidth: 208,
    offsetLeft: -9, offsetTop: -14, petAnchorX: 96, petBaselineY: 203,
  });
});

test("manifest is complete, sorted and hash verified", async () => {
  const manifest = JSON.parse(await fs.readFile(path.join(first.petRoot, MANIFEST_NAME)));
  assert.equal(manifest.formatVersion, 1);
  assert.equal(manifest.petId, PET_ID);
  assert.equal(Object.keys(manifest.files).length, 23);
  assert.deepEqual(Object.keys(manifest.files), [...Object.keys(manifest.files)].sort((a, b) => a.localeCompare(b, "en")));
  assert.equal(MANIFEST_NAME in manifest.files, false);
  assert.equal((await validatePayload(first.petRoot)).ok, true);
});

test("two builds have identical bytes and hashes", async () => {
  assert.deepEqual(first.manifest, second.manifest);
  assert.equal(await sha256File(path.join(first.petRoot, MANIFEST_NAME)), await sha256File(path.join(second.petRoot, MANIFEST_NAME)));
  for (const relative of Object.keys(first.manifest.files)) {
    assert.equal(await sha256File(path.join(first.petRoot, relative)), await sha256File(path.join(second.petRoot, relative)));
  }
});

test("payload metadata contains no absolute or machine-specific paths", async () => {
  for (const relative of ["pet.json", "liang-runtime.json", MANIFEST_NAME]) {
    const text = await fs.readFile(path.join(first.petRoot, relative), "utf8");
    assert.equal(text.includes(PROJECT_ROOT), false);
    assert.equal(text.includes(os.homedir()), false);
    assert.equal(text.includes("/Users/"), false);
  }
});

test("payload contains no symlink", async () => {
  const symlinkRoot = path.join(root, "symlink");
  const built = await buildPetPayload({ outputRoot: symlinkRoot });
  await fs.symlink(path.join(built.petRoot, "pet.json"), path.join(built.petRoot, "unexpected-link"));
  await assert.rejects(validatePayload(built.petRoot), /symlink rejected/);
});

test("relative path policy rejects traversal and absolute paths", () => {
  for (const value of ["../escape", "forms/../escape", "/absolute", "C:/absolute", "forms\\gu", "./pet.json", "a//b"]) {
    assert.equal(isSafeRelativePath(value), false, value);
  }
  assert.equal(isSafeRelativePath("forms/gu/spritesheet.webp"), true);
});

test("source assets are unchanged by both builds", async () => {
  assert.deepEqual(await sourceSnapshot(), sourceHashes);
});

test("existing output is refused rather than overwritten", async () => {
  await assert.rejects(buildPetPayload({ outputRoot: path.join(root, "first") }), /already exists/);
});
