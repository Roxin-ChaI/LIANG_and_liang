/** Frozen oversized Phase 3D transition assets, loaded once outside playback. */
import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const PROJECT_ROOT = fileURLToPath(new URL("../../", import.meta.url));
const PNG_SIGNATURE = Buffer.from("89504e470d0a1a0a", "hex");
export const TRANSITION_SPECS = Object.freeze({
  gu_to_feng: Object.freeze({ count: 10, width: 224, height: 240, from: "gu", to: "feng" }),
  feng_to_gu: Object.freeze({ count: 8, width: 208, height: 224, from: "feng", to: "gu" }),
});

function fail(message) { throw new TypeError(`INVALID_TRANSITION_ASSETS ${message}`); }
function sha(bytes) { return crypto.createHash("sha256").update(bytes).digest("hex"); }

function pngDimensions(bytes) {
  if (!Buffer.isBuffer(bytes) || bytes.length < 33
      || !bytes.subarray(0, 8).equals(PNG_SIGNATURE)
      || bytes.toString("ascii", 12, 16) !== "IHDR"
      || bytes.readUInt32BE(8) !== 13
      || bytes[24] !== 8 || bytes[25] !== 6) {
    fail("frame must be an 8-bit RGBA PNG");
  }
  return Object.freeze({ width: bytes.readUInt32BE(16), height: bytes.readUInt32BE(20) });
}

function validateLayout(layout, name, spec) {
  if (!layout || layout.canvasWidth !== spec.width || layout.canvasHeight !== spec.height
      || layout.petAnchorX !== 96 || layout.petBaselineY !== 203
      || layout.offsetLeft !== 96 - layout.anchorX
      || layout.offsetTop !== 203 - layout.anchorY) {
    fail(`${name} layout is not the frozen anchor/canvas`);
  }
  return Object.freeze({ ...layout });
}

/** Verify the frozen SHA manifest, exact order and RGBA canvas; retain no bytes. */
export async function loadTransitionAssets({ projectRoot = PROJECT_ROOT, readFile = fs.readFile } = {}) {
  const manifest = (await readFile(path.join(projectRoot, "assets/transform-overlay.sha256"))).toString("utf8");
  const checksumRows = manifest.trimEnd().split("\n");
  const expectedRows = Object.values(TRANSITION_SPECS).reduce((sum, spec) => sum + spec.count, 0);
  if (checksumRows.length !== expectedRows) fail(`checksum manifest must contain ${expectedRows} rows`);
  const layoutFixture = JSON.parse((await readFile(path.join(
    projectRoot, "runtime-patch/fixtures/transition-overlay-layout.json",
  ))).toString("utf8"));
  const result = {};
  let manifestIndex = 0;
  for (const [name, spec] of Object.entries(TRANSITION_SPECS)) {
    const layout = validateLayout(layoutFixture[name], name, spec);
    const frames = [];
    for (let index = 1; index <= spec.count; index += 1) {
      const source = `assets/transform-overlay/${name}/${name}_${String(index).padStart(2, "0")}.png`;
      const row = checksumRows[manifestIndex++];
      const match = /^([a-f0-9]{64})  (\S+)$/.exec(row);
      if (!match || match[2] !== source) fail(`manifest order/path mismatch at ${source}`);
      const bytes = await readFile(path.join(projectRoot, source));
      const dimensions = pngDimensions(bytes);
      if (dimensions.width !== spec.width || dimensions.height !== spec.height || sha(bytes) !== match[1]) {
        fail(`${source} differs from frozen RGBA overlay frame`);
      }
      frames.push(Object.freeze({ source, sha256: match[1], ...dimensions }));
    }
    result[name] = Object.freeze({
      from: spec.from, to: spec.to, frameDurationMs: 140,
      frames: Object.freeze(frames), layout,
    });
  }
  return Object.freeze(result);
}
