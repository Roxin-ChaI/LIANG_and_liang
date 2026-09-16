#!/usr/bin/env node
/** Deterministic production payload builder for Liang no Henshin. */

import crypto from "node:crypto";
import fs from "node:fs";
import fsp from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { parseWebPDimensions } from "../runtime-patch/prototype/dual-atlas-loader.mjs";
import { validateRuntimeConfig } from "../runtime-patch/reference/runtime-state.mjs";

export const PROJECT_ROOT = fileURLToPath(new URL("../", import.meta.url));
export const PET_DIRECTORY = "liang-no-henshin";
export const PET_ID = "custom:liang-no-henshin";
export const NATIVE_ID = "liang-no-henshin";
export const DISPLAY_NAME = "Liang no Henshin";
export const MANIFEST_NAME = ".liang-install-manifest.json";

const SOURCES = Object.freeze({
  gu: path.join(PROJECT_ROOT, "assets/builds/gu/spritesheet.webp"),
  feng: path.join(PROJECT_ROOT, "assets/builds/feng/spritesheet.webp"),
  layouts: path.join(PROJECT_ROOT, "runtime-patch/fixtures/transition-overlay-layout.json"),
  schedule: path.join(PROJECT_ROOT, "runtime-patch/fixtures/transition-scale-schedule.json"),
  gu_to_feng: path.join(PROJECT_ROOT, "assets/transform-overlay/gu_to_feng"),
  feng_to_gu: path.join(PROJECT_ROOT, "assets/transform-overlay/feng_to_gu"),
});

const TRANSITIONS = Object.freeze({
  gu_to_feng: Object.freeze({ from: "gu", to: "feng", count: 10 }),
  feng_to_gu: Object.freeze({ from: "feng", to: "gu", count: 8 }),
});

export function sha256(buffer) {
  return crypto.createHash("sha256").update(buffer).digest("hex");
}

export async function sha256File(file) {
  const hash = crypto.createHash("sha256");
  for await (const chunk of fs.createReadStream(file)) hash.update(chunk);
  return hash.digest("hex");
}

function stableJson(value) {
  return `${JSON.stringify(value, null, 2)}\n`;
}

export function isSafeRelativePath(value) {
  if (typeof value !== "string" || value.length === 0 || value.includes("\0") || value.includes("\\")) return false;
  if (path.posix.isAbsolute(value) || /^[A-Za-z]:/.test(value)) return false;
  return value.split("/").every(segment => segment.length > 0 && segment !== "." && segment !== "..");
}

function assertInside(root, candidate, label) {
  const relative = path.relative(root, candidate);
  if (relative === "" || relative === ".." || relative.startsWith(`..${path.sep}`) || path.isAbsolute(relative)) {
    throw Error(`${label} escapes payload root`);
  }
}

async function copyRegular(source, destination) {
  const sourceStat = await fsp.lstat(source);
  if (!sourceStat.isFile() || sourceStat.isSymbolicLink()) throw Error(`source is not a regular file: ${source}`);
  await fsp.mkdir(path.dirname(destination), { recursive: true });
  await fsp.copyFile(source, destination, fs.constants.COPYFILE_EXCL);
}

function pngMetadata(bytes, label) {
  const signature = "89504e470d0a1a0a";
  if (bytes.length < 33 || bytes.subarray(0, 8).toString("hex") !== signature
      || bytes.toString("ascii", 12, 16) !== "IHDR") throw Error(`${label} is not a valid PNG`);
  return Object.freeze({
    width: bytes.readUInt32BE(16),
    height: bytes.readUInt32BE(20),
    bitDepth: bytes[24],
    colorType: bytes[25],
  });
}

async function listTransitionSources(name) {
  const sourceDirectory = SOURCES[name];
  const entries = (await fsp.readdir(sourceDirectory, { withFileTypes: true }))
    .filter(entry => entry.name.endsWith(".png"))
    .sort((left, right) => left.name.localeCompare(right.name, "en"));
  if (entries.length !== TRANSITIONS[name].count || entries.some(entry => !entry.isFile() || entry.isSymbolicLink())) {
    throw Error(`${name} must contain exactly ${TRANSITIONS[name].count} regular PNG frames`);
  }
  return entries.map(entry => path.join(sourceDirectory, entry.name));
}

async function makeRuntimeSidecar() {
  const layouts = JSON.parse(await fsp.readFile(SOURCES.layouts, "utf8"));
  const schedule = JSON.parse(await fsp.readFile(SOURCES.schedule, "utf8"));
  const transitions = {};
  for (const [name, spec] of Object.entries(TRANSITIONS)) {
    const sources = await listTransitionSources(name);
    if (!Array.isArray(schedule[name]) || schedule[name].length !== spec.count) {
      throw Error(`${name} scale schedule does not match frame count`);
    }
    const layout = layouts[name];
    if (layout.offsetLeft !== layout.petAnchorX - layout.anchorX
        || layout.offsetTop !== layout.petBaselineY - layout.anchorY) {
      throw Error(`${name} overlay layout anchor offsets are inconsistent`);
    }
    transitions[name] = {
      from: spec.from,
      to: spec.to,
      frames: sources.map(source => `transitions/${name}/${path.basename(source)}`),
      frameDurationMs: 140,
      layout,
    };
  }
  const sidecar = {
    schemaVersion: 1,
    initialForm: "gu",
    forms: {
      gu: { spritesheetPath: "forms/gu/spritesheet.webp" },
      feng: { spritesheetPath: "forms/feng/spritesheet.webp" },
    },
    transitions,
  };
  const validation = validateRuntimeConfig(sidecar);
  if (!validation.valid) throw Error(`generated sidecar invalid: ${validation.errors.join("; ")}`);
  return sidecar;
}

async function payloadFiles(root) {
  const files = [];
  async function visit(directory) {
    const entries = await fsp.readdir(directory, { withFileTypes: true });
    entries.sort((left, right) => left.name.localeCompare(right.name, "en"));
    for (const entry of entries) {
      const absolute = path.join(directory, entry.name);
      const relative = path.relative(root, absolute).split(path.sep).join("/");
      if (entry.isSymbolicLink()) throw Error(`payload symlink rejected: ${relative}`);
      if (entry.isDirectory()) await visit(absolute);
      else if (entry.isFile() && relative !== MANIFEST_NAME) files.push(relative);
      else if (!entry.isFile()) throw Error(`non-regular payload entry rejected: ${relative}`);
    }
  }
  await visit(root);
  return files;
}

export async function validatePayload(petRoot) {
  const root = await fsp.realpath(petRoot);
  const rootStat = await fsp.lstat(petRoot);
  if (!rootStat.isDirectory() || rootStat.isSymbolicLink()) throw Error("payload root must be a real directory");
  const manifest = JSON.parse(await fsp.readFile(path.join(root, MANIFEST_NAME), "utf8"));
  if (manifest.formatVersion !== 1 || manifest.petId !== PET_ID || typeof manifest.files !== "object") {
    throw Error("invalid install manifest identity");
  }
  const actualFiles = await payloadFiles(root);
  const listedFiles = Object.keys(manifest.files).sort((a, b) => a.localeCompare(b, "en"));
  if (JSON.stringify(actualFiles) !== JSON.stringify(listedFiles)) throw Error("install manifest file set mismatch");
  for (const relative of listedFiles) {
    if (!isSafeRelativePath(relative)) throw Error(`unsafe manifest path: ${relative}`);
    const absolute = path.resolve(root, relative);
    assertInside(root, absolute, relative);
    const details = await fsp.lstat(absolute);
    if (!details.isFile() || details.isSymbolicLink()) throw Error(`manifest entry is not a regular file: ${relative}`);
    if (await sha256File(absolute) !== manifest.files[relative]) throw Error(`manifest hash mismatch: ${relative}`);
  }
  const pet = JSON.parse(await fsp.readFile(path.join(root, "pet.json"), "utf8"));
  if (pet.id !== NATIVE_ID || pet.displayName !== DISPLAY_NAME || pet.spriteVersionNumber !== 2
      || pet.spritesheetPath !== "spritesheet.webp") throw Error("native pet manifest mismatch");
  const sidecar = JSON.parse(await fsp.readFile(path.join(root, "liang-runtime.json"), "utf8"));
  const sidecarValidation = validateRuntimeConfig(sidecar);
  if (!sidecarValidation.valid || sidecar.schemaVersion !== 1 || sidecar.initialForm !== "gu") {
    throw Error(`runtime sidecar invalid: ${sidecarValidation.errors.join("; ")}`);
  }
  for (const atlas of ["spritesheet.webp", "forms/gu/spritesheet.webp", "forms/feng/spritesheet.webp"]) {
    const dimensions = parseWebPDimensions(await fsp.readFile(path.join(root, atlas)));
    if (dimensions.width !== 1536 || dimensions.height !== 2288) throw Error(`${atlas} must be 1536x2288`);
  }
  if (await sha256File(path.join(root, "spritesheet.webp"))
      !== await sha256File(path.join(root, "forms/gu/spritesheet.webp"))) throw Error("native fallback must equal Gu atlas");
  for (const [name, spec] of Object.entries(TRANSITIONS)) {
    const transition = sidecar.transitions[name];
    if (transition.frames.length !== spec.count || transition.frameDurationMs !== 140) throw Error(`${name} metadata mismatch`);
    for (const relative of transition.frames) {
      if (!isSafeRelativePath(relative)) throw Error(`unsafe transition path: ${relative}`);
      const metadata = pngMetadata(await fsp.readFile(path.join(root, relative)), relative);
      if (metadata.width !== transition.layout.canvasWidth || metadata.height !== transition.layout.canvasHeight
          || metadata.bitDepth !== 8 || metadata.colorType !== 6) throw Error(`${relative} does not match RGBA canvas metadata`);
    }
  }
  return Object.freeze({ ok: true, petRoot: root, manifest, pet, sidecar });
}

export async function buildPetPayload({ outputRoot = path.join(PROJECT_ROOT, "build/pet-payload") } = {}) {
  const absoluteOutput = path.resolve(outputRoot);
  if (absoluteOutput === path.parse(absoluteOutput).root) throw Error("refusing filesystem-root output");
  const petRoot = path.join(absoluteOutput, PET_DIRECTORY);
  try {
    await fsp.mkdir(absoluteOutput, { recursive: true });
    await fsp.mkdir(petRoot);
  } catch (error) {
    if (error.code === "EEXIST") throw Error(`payload destination already exists: ${petRoot}`);
    throw error;
  }

  await copyRegular(SOURCES.gu, path.join(petRoot, "spritesheet.webp"));
  await copyRegular(SOURCES.gu, path.join(petRoot, "forms/gu/spritesheet.webp"));
  await copyRegular(SOURCES.feng, path.join(petRoot, "forms/feng/spritesheet.webp"));
  for (const name of Object.keys(TRANSITIONS)) {
    for (const source of await listTransitionSources(name)) {
      await copyRegular(source, path.join(petRoot, "transitions", name, path.basename(source)));
    }
  }
  const pet = {
    id: NATIVE_ID,
    displayName: DISPLAY_NAME,
    description: "Single-ID Codex Pet with Gu fallback and patched dual-form runtime metadata.",
    spriteVersionNumber: 2,
    spritesheetPath: "spritesheet.webp",
  };
  await fsp.writeFile(path.join(petRoot, "pet.json"), stableJson(pet), { flag: "wx" });
  await fsp.writeFile(path.join(petRoot, "liang-runtime.json"), stableJson(await makeRuntimeSidecar()), { flag: "wx" });
  const files = {};
  for (const relative of await payloadFiles(petRoot)) files[relative] = await sha256File(path.join(petRoot, relative));
  const manifest = { formatVersion: 1, petId: PET_ID, files };
  await fsp.writeFile(path.join(petRoot, MANIFEST_NAME), stableJson(manifest), { flag: "wx" });
  await validatePayload(petRoot);
  return Object.freeze({ outputRoot: absoluteOutput, petRoot, manifest });
}

async function main() {
  const args = process.argv.slice(2);
  const outputIndex = args.indexOf("--output");
  if (args.length !== 2 || outputIndex !== 0) throw Error("usage: pet-payload.mjs --output <directory>");
  const built = await buildPetPayload({ outputRoot: args[1] });
  console.log(`payload=${built.petRoot}`);
  console.log("validation=PASS");
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch(error => {
    console.error(`payload_error=${error.message}`);
    process.exitCode = 1;
  });
}
