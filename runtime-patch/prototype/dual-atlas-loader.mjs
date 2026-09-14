import fs from "node:fs/promises";
import path from "node:path";

import { validateRuntimeConfig } from "../reference/runtime-state.mjs";

const V2_WIDTH = 1536;
const V2_HEIGHT = 2288;

export class DualAtlasLoadError extends Error {
  constructor(code, message, options) {
    super(message, options);
    this.name = "DualAtlasLoadError";
    this.code = code;
  }
}

function fail(code, message, cause) {
  throw new DualAtlasLoadError(code, message, cause ? { cause } : undefined);
}

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function normalizePetId(id, petRoot) {
  if (typeof id === "string" && id.length > 0) {
    return id.startsWith("custom:") ? id : `custom:${id}`;
  }
  return `custom:${path.basename(petRoot)}`;
}

async function readJson(filePath, readFile, errorCode) {
  let bytes;
  try {
    bytes = await readFile(filePath);
  } catch (error) {
    fail(errorCode, `Unable to read ${path.basename(filePath)}`, error);
  }
  try {
    return JSON.parse(bytes.toString("utf8"));
  } catch (error) {
    fail(errorCode, `Malformed JSON in ${path.basename(filePath)}`, error);
  }
}

async function optionalJson(filePath, readFile) {
  try {
    return await readJson(filePath, readFile, "MALFORMED_SIDECAR");
  } catch (error) {
    if (error.cause?.code === "ENOENT") return null;
    throw error;
  }
}

function validateNativeManifest(manifest) {
  if (!isObject(manifest)) fail("MALFORMED_NATIVE_MANIFEST", "pet.json must contain an object");
  if (!Number.isInteger(manifest.spriteVersionNumber)) {
    fail("MALFORMED_NATIVE_MANIFEST", "pet.json spriteVersionNumber must be an integer");
  }
  if (typeof manifest.spritesheetPath !== "string" || manifest.spritesheetPath.length === 0) {
    fail("MALFORMED_NATIVE_MANIFEST", "pet.json spritesheetPath must be a non-empty string");
  }
}

function isPathInside(root, candidate) {
  const relative = path.relative(root, candidate);
  return relative !== "" && !relative.startsWith(`..${path.sep}`) && relative !== ".." && !path.isAbsolute(relative);
}

async function resolveContainedFile(rootRealPath, relativePath, realpath) {
  const lexical = path.resolve(rootRealPath, relativePath);
  if (!isPathInside(rootRealPath, lexical)) {
    fail("PATH_ESCAPE", `Path escapes Pet root: ${relativePath}`);
  }

  let resolved;
  try {
    resolved = await realpath(lexical);
  } catch (error) {
    fail("ASSET_MISSING", `Asset does not exist: ${relativePath}`, error);
  }
  if (!isPathInside(rootRealPath, resolved)) {
    fail("PATH_ESCAPE", `Resolved path escapes Pet root: ${relativePath}`);
  }
  return resolved;
}

function readUInt24LE(buffer, offset) {
  return buffer[offset] | (buffer[offset + 1] << 8) | (buffer[offset + 2] << 16);
}

/** Parse dimensions directly from VP8, VP8L, or VP8X WebP headers. */
export function parseWebPDimensions(buffer) {
  if (!Buffer.isBuffer(buffer) || buffer.length < 20) {
    fail("INVALID_WEBP", "Atlas is empty or too short to be WebP");
  }
  if (buffer.toString("ascii", 0, 4) !== "RIFF" || buffer.toString("ascii", 8, 12) !== "WEBP") {
    fail("INVALID_WEBP", "Atlas does not have a WebP RIFF header");
  }
  const declaredEnd = buffer.readUInt32LE(4) + 8;
  if (declaredEnd > buffer.length) fail("INVALID_WEBP", "WebP RIFF length exceeds file size");

  let offset = 12;
  while (offset + 8 <= declaredEnd) {
    const chunkType = buffer.toString("ascii", offset, offset + 4);
    const chunkLength = buffer.readUInt32LE(offset + 4);
    const dataOffset = offset + 8;
    const dataEnd = dataOffset + chunkLength;
    if (dataEnd > declaredEnd) fail("INVALID_WEBP", "WebP chunk exceeds RIFF length");

    if (chunkType === "VP8X") {
      if (chunkLength < 10) fail("INVALID_WEBP", "VP8X chunk is too short");
      return { width: readUInt24LE(buffer, dataOffset + 4) + 1, height: readUInt24LE(buffer, dataOffset + 7) + 1 };
    }
    if (chunkType === "VP8L") {
      if (chunkLength < 5 || buffer[dataOffset] !== 0x2f) fail("INVALID_WEBP", "Invalid VP8L header");
      const bits = buffer.readUInt32LE(dataOffset + 1);
      return { width: (bits & 0x3fff) + 1, height: ((bits >>> 14) & 0x3fff) + 1 };
    }
    if (chunkType === "VP8 ") {
      if (
        chunkLength < 10
        || buffer[dataOffset + 3] !== 0x9d
        || buffer[dataOffset + 4] !== 0x01
        || buffer[dataOffset + 5] !== 0x2a
      ) {
        fail("INVALID_WEBP", "Invalid VP8 frame header");
      }
      return {
        width: buffer.readUInt16LE(dataOffset + 6) & 0x3fff,
        height: buffer.readUInt16LE(dataOffset + 8) & 0x3fff,
      };
    }
    offset = dataEnd + (chunkLength % 2);
  }
  fail("INVALID_WEBP", "WebP has no supported image chunk");
}

async function loadAtlas({ form, source, petRootRealPath, readFile, realpath }) {
  const absolutePath = await resolveContainedFile(petRootRealPath, source.spritesheetPath, realpath);
  let bytes;
  try {
    bytes = await readFile(absolutePath);
  } catch (error) {
    fail("ATLAS_READ_FAILED", `Unable to read ${form} atlas`, error);
  }
  if (bytes.length === 0) fail("INVALID_WEBP", `${form} atlas is empty`);
  const { width, height } = parseWebPDimensions(bytes);
  if (width !== V2_WIDTH || height !== V2_HEIGHT) {
    fail("INVALID_ATLAS_DIMENSIONS", `${form} atlas must be ${V2_WIDTH}x${V2_HEIGHT}; got ${width}x${height}`);
  }
  return Object.freeze({
    spritesheetPath: source.spritesheetPath,
    spritesheetDataUrl: `data:image/webp;base64,${bytes.toString("base64")}`,
    width,
    height,
  });
}

/**
 * Load a native Pet plus the optional Liang runtime sidecar.
 * No cross-invocation cache or mutable global state is retained.
 */
export async function loadDualFormAvatar({ petRoot, nativeManifest, io = {} }) {
  if (typeof petRoot !== "string" || petRoot.length === 0) {
    fail("INVALID_PET_ROOT", "petRoot must be a non-empty path");
  }
  const readFile = io.readFile ?? fs.readFile;
  const realpath = io.realpath ?? fs.realpath;

  let petRootRealPath;
  try {
    petRootRealPath = await realpath(petRoot);
  } catch (error) {
    fail("INVALID_PET_ROOT", "petRoot does not exist", error);
  }

  const manifest = nativeManifest ?? await readJson(
    path.join(petRootRealPath, "pet.json"),
    readFile,
    "MALFORMED_NATIVE_MANIFEST",
  );
  validateNativeManifest(manifest);

  const native = Object.freeze({
    ...manifest,
    petId: normalizePetId(manifest.id, petRootRealPath),
  });
  const sidecar = await optionalJson(path.join(petRootRealPath, "liang-runtime.json"), readFile);
  if (sidecar === null) {
    return Object.freeze({ mode: "native-only", native });
  }

  const sidecarValidation = validateRuntimeConfig(sidecar);
  if (!sidecarValidation.valid) {
    fail("INVALID_SIDECAR", sidecarValidation.errors.join("; "));
  }
  if (manifest.spriteVersionNumber !== 2) {
    fail("UNSUPPORTED_SPRITE_VERSION", "Dual-form prototype requires spriteVersionNumber 2");
  }

  const forms = {};
  for (const form of ["gu", "feng"]) {
    forms[form] = await loadAtlas({
      form,
      source: sidecar.forms[form],
      petRootRealPath,
      readFile,
      realpath,
    });
  }

  return Object.freeze({
    mode: "dual-form",
    schemaVersion: sidecar.schemaVersion,
    initialForm: sidecar.initialForm,
    native,
    forms: Object.freeze(forms),
    transitions: sidecar.transitions,
  });
}
