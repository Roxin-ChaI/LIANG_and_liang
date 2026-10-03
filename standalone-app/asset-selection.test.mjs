import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { createAssetReader } from "./asset-selection.mjs";
import { loadTransitionAssets } from "../runtime-patch/prototype/transition-assets.mjs";
const root = path.resolve(import.meta.dirname, "..");

test("selected forward assets pass existing transition verifier; reverse stays frozen", async () => {
  const readFile = await createAssetReader(root);
  const assets = await loadTransitionAssets({ projectRoot: root, readFile });
  assert.ok(assets);
  const relative = "assets/transform-overlay/feng_to_gu/feng_to_gu_01.png";
  assert.deepEqual(await readFile(path.join(root, relative)), await fs.readFile(path.join(root, relative)));
  assert.notDeepEqual(await readFile(path.join(root, "assets/builds/gu/spritesheet.webp")),
    await fs.readFile(path.join(root, "assets/builds/gu/spritesheet.webp")));
});
test("packaged no-config fallback and path escape rejection", async () => {
  const temporary = await fs.mkdtemp(path.join(os.tmpdir(), "lnh-assets-"));
  try {
    await fs.writeFile(path.join(temporary, "sample"), "original");
    const read = await createAssetReader(temporary);
    assert.equal(await read(path.join(temporary, "sample"), "utf8"), "original");
    await fs.mkdir(path.join(temporary, "standalone-app"));
    await fs.writeFile(path.join(temporary, "standalone-app/asset-overrides.json"),
      JSON.stringify({"assets/a": "assets/../../outside"}));
    await assert.rejects(createAssetReader(temporary), /inside project/);
  } finally { await fs.rm(temporary, {recursive: true, force: true}); }
});
