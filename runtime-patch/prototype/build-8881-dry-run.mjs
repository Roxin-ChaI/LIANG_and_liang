import { execFileSync } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import fsp from "node:fs/promises";
import os from "node:os";
import path from "node:path";

const APP_ROOT = "/Applications/ChatGPT.app";
const INFO_PLIST = path.join(APP_ROOT, "Contents/Info.plist");
const ASAR_PATH = path.join(APP_ROOT, "Contents/Resources/app.asar");

const EXPECTED = Object.freeze({
  version: "26.908.40834",
  build: "8881",
  appAsar: "bb40cd8811887363104a19291346af9595632e0e956316a1086b274fb8e3eafc",
  main: "0765260be74e8843630d5a92e30bca574783892688e67180c119a5c58679bb61",
  core: "737070f94a072d2b4ede9f326e3e1c4142fb82198961251c2e70479b3f926275",
  overlay: "9ddf6ce3bb7a6b2276d2b598afc3bb14f3424e5b4d1bb452378d5fbe0dfa5f49",
});

const TARGETS = Object.freeze({
  main: ".vite/build/main-DaMR-wdT.js",
  core: "webview/assets/app-initial-9b95fa538c62.js",
  overlay: "webview/assets/avatar-overlay-native-page-bb89afb2a8f6.js",
});

const MAIN_PATCH_SITE = "loadAvatar(e){return n.Mt({appServerClient:this.executionHostRegistry.get(),avatarId:e,preferWsl:!!process.env.WSL_DISTRO_NAME})}";
const MAIN_REPLACEMENT = "loadAvatar(e){return n.Mt({appServerClient:this.executionHostRegistry.get(),avatarId:e,preferWsl:!!process.env.WSL_DISTRO_NAME}).then(e=>e==null?e:{...e,spritesheetDataUrl:e.spritesheetDataUrl,runtimeForms:e.runtimeForms??null,runtimeInitialForm:e.runtimeInitialForm??null})}";
const CORE_PATCH_SITE = "spritesheetUrl:e.spritesheetDataUrl,upgradeDirectoryPath:t<2?e.directoryPath:void 0";
const CORE_REPLACEMENT = "spritesheetUrl:e.spritesheetDataUrl,runtimeForms:e.runtimeForms,runtimeInitialForm:e.runtimeInitialForm,upgradeDirectoryPath:t<2?e.directoryPath:void 0";
const OVERLAY_PATCH_SITE = "source:Kr(c)";
const OVERLAY_REPLACEMENT = "source:Kr(c.runtimeForms?{...c,spritesheetUrl:c.runtimeForms[c.runtimeCurrentForm??c.runtimeInitialForm??`gu`]??c.spritesheetUrl}:c)";
const COMPLETE_STATE_MAP = "Xlo={failed:i4(5,8,140,240),idle:Jlo,jumping:i4(4,5,140,280),review:i4(8,6,150,280),running:i4(7,6,120,220),\"running-left\":i4(2,8,120,220),\"running-right\":i4(1,8,120,220),waving:i4(3,4,140,280),waiting:i4(6,6,150,260)}";

function sha256(buffer) {
  return crypto.createHash("sha256").update(buffer).digest("hex");
}

async function sha256File(filePath) {
  const hash = crypto.createHash("sha256");
  for await (const chunk of fs.createReadStream(filePath)) hash.update(chunk);
  return hash.digest("hex");
}

function countOccurrences(source, needle) {
  let count = 0;
  let offset = 0;
  while ((offset = source.indexOf(needle, offset)) !== -1) {
    count += 1;
    offset += needle.length;
  }
  return count;
}

function requireCount(source, needle, expected, label) {
  const actual = countOccurrences(source, needle);
  if (actual !== expected) throw new Error(`${label}: expected ${expected} match, got ${actual}`);
  return actual;
}

function readPlistValue(key) {
  return execFileSync("/usr/libexec/PlistBuddy", ["-c", `Print :${key}`, INFO_PLIST], {
    encoding: "utf8",
  }).trim();
}

function readArchive() {
  const descriptor = fs.openSync(ASAR_PATH, "r");
  try {
    const prefix = Buffer.alloc(8);
    if (fs.readSync(descriptor, prefix, 0, prefix.length, 0) !== prefix.length) {
      throw new Error("ASAR prefix is truncated");
    }
    const headerSize = prefix.readUInt32LE(4);
    const headerBuffer = Buffer.alloc(headerSize);
    if (fs.readSync(descriptor, headerBuffer, 0, headerSize, 8) !== headerSize) {
      throw new Error("ASAR header is truncated");
    }
    const jsonLength = headerBuffer.readUInt32LE(4);
    const header = JSON.parse(headerBuffer.toString("utf8", 8, 8 + jsonLength));
    return { descriptor, header, dataOffset: 8 + headerSize };
  } catch (error) {
    fs.closeSync(descriptor);
    throw error;
  }
}

function findArchiveEntry(header, archivePath) {
  let entry = header;
  for (const segment of archivePath.split("/")) {
    entry = entry?.files?.[segment];
    if (!entry) throw new Error(`ASAR entry not found: ${archivePath}`);
  }
  if (entry.unpacked || entry.link || !Number.isSafeInteger(entry.size) || !/^\d+$/.test(entry.offset)) {
    throw new Error(`ASAR entry is not a regular packed file: ${archivePath}`);
  }
  return entry;
}

function extractTargetsToMemory() {
  const archive = readArchive();
  try {
    return Object.fromEntries(Object.entries(TARGETS).map(([name, archivePath]) => {
      const entry = findArchiveEntry(archive.header, archivePath);
      const buffer = Buffer.alloc(entry.size);
      const bytesRead = fs.readSync(
        archive.descriptor,
        buffer,
        0,
        entry.size,
        archive.dataOffset + Number(entry.offset),
      );
      if (bytesRead !== entry.size) throw new Error(`ASAR entry is truncated: ${archivePath}`);
      return [name, buffer];
    }));
  } finally {
    fs.closeSync(archive.descriptor);
  }
}

async function captureFingerprint() {
  const chunks = extractTargetsToMemory();
  const stat = await fsp.stat(ASAR_PATH);
  return Object.freeze({
    version: readPlistValue("CFBundleShortVersionString"),
    build: readPlistValue("CFBundleVersion"),
    appAsar: await sha256File(ASAR_PATH),
    main: sha256(chunks.main),
    core: sha256(chunks.core),
    overlay: sha256(chunks.overlay),
    asarSize: stat.size,
    asarMode: stat.mode,
    asarMtimeMs: stat.mtimeMs,
    chunks,
  });
}

function assertExpectedFingerprint(fingerprint) {
  for (const key of ["version", "build", "appAsar", "main", "core", "overlay"]) {
    if (fingerprint[key] !== EXPECTED[key]) {
      throw new Error(`Fingerprint mismatch for ${key}: ${fingerprint[key]}`);
    }
  }
}

function assertOriginalIntegrity(before, after) {
  for (const key of [
    "version",
    "build",
    "appAsar",
    "main",
    "core",
    "overlay",
    "asarSize",
    "asarMode",
    "asarMtimeMs",
  ]) {
    if (before[key] !== after[key]) throw new Error(`Original integrity changed: ${key}`);
  }
}

function locatePatchSites(sources) {
  const mainMatches = requireCount(sources.main, MAIN_PATCH_SITE, 1, "main patch site");
  requireCount(sources.main, "var iR=class extends n.xf", 1, "main custom-avatar service class");
  requireCount(sources.main, "customAvatars:new iR", 1, "main service registration");

  const overlayMatches = requireCount(sources.overlay, OVERLAY_PATCH_SITE, 1, "overlay patch site");
  requireCount(sources.overlay, "function kd(){", 1, "overlay selected-avatar hook");
  requireCount(sources.overlay, "Ae(ze,n??t.id)", 1, "overlay custom by-ID query alias");
  requireCount(sources.overlay, "tT as Kr", 1, "overlay Alo import alias");
  if (countOccurrences(sources.overlay, "mascotDragState") < 1) {
    throw new Error("overlay drag-state anchor is absent");
  }

  const coreMatches = requireCount(sources.core, CORE_PATCH_SITE, 1, "core option-model patch site");
  requireCount(sources.core, "function Alo(e)", 1, "core Alo source converter");
  requireCount(sources.core, "Alo as tT", 1, "core Alo export");
  requireCount(sources.core, "ruo as Uw", 1, "core renderer export");
  requireCount(sources.core, '"data-codex-pet-state":u', 1, "core renderer state attribute");
  requireCount(sources.core, COMPLETE_STATE_MAP, 1, "core complete state map");

  return Object.freeze({ main: mainMatches, overlay: overlayMatches, core: coreMatches });
}

function patchExactlyOnce(source, before, after, label) {
  requireCount(source, before, 1, label);
  return source.replace(before, after);
}

function assertPatchedStaticContract(patched) {
  requireCount(patched.main, "customAvatars:new iR", 1, "patched main service anchor");
  requireCount(patched.main, "spritesheetDataUrl:e.spritesheetDataUrl", 1, "native spritesheet field");
  requireCount(patched.main, "runtimeForms:e.runtimeForms??null", 1, "dual atlas result field");

  requireCount(patched.core, "function Alo(e)", 1, "patched Alo anchor");
  requireCount(patched.core, COMPLETE_STATE_MAP, 1, "patched complete state map");
  requireCount(patched.core, "ruo as Uw", 1, "patched renderer export");
  requireCount(patched.core, "spritesheetUrl:e.spritesheetDataUrl", 1, "single-atlas option fallback");
  requireCount(patched.core, "runtimeForms:e.runtimeForms", 1, "dual atlas option propagation");

  requireCount(patched.overlay, "function kd(){", 1, "patched selected-avatar anchor");
  requireCount(patched.overlay, "source:Kr(", 1, "patched source converter call");
  requireCount(patched.overlay, "c.runtimeForms?", 1, "dual atlas source branch");
  requireCount(patched.overlay, "c.runtimeInitialForm??`gu`", 1, "sidecar initial-form branch");
  requireCount(patched.overlay, "??c.spritesheetUrl", 1, "single-atlas source fallback");
}

async function writeAndCheckPatchedCopies(tempRoot, patched) {
  for (const [name, source] of Object.entries(patched)) {
    const filePath = path.join(tempRoot, `${name}.patched.js`);
    await fsp.writeFile(filePath, source);
    execFileSync(process.execPath, ["--check", filePath], { stdio: "pipe" });
  }
}

async function writeExtractedCopies(tempRoot, chunks) {
  for (const [name, buffer] of Object.entries(chunks)) {
    await fsp.writeFile(path.join(tempRoot, `${name}.original.js`), buffer);
  }
}

async function run() {
  let tempRoot = null;
  let cleanupResult = "NOT_REQUIRED";
  try {
    const before = await captureFingerprint();
    assertExpectedFingerprint(before);
    console.log("fingerprint=PASS");
    console.log(`version=${before.version}`);
    console.log(`build=${before.build}`);
    console.log(`app_asar_sha256=${before.appAsar}`);

    tempRoot = await fsp.mkdtemp(path.join(os.tmpdir(), "liang-build-8881-dry-run-"));
    await writeExtractedCopies(tempRoot, before.chunks);
    const sources = Object.fromEntries(await Promise.all(
      Object.keys(before.chunks).map(async (name) => [
        name,
        await fsp.readFile(path.join(tempRoot, `${name}.original.js`), "utf8"),
      ]),
    ));
    const matches = locatePatchSites(sources);
    console.log(`main_patch_site_matches=${matches.main}`);
    console.log(`overlay_patch_site_matches=${matches.overlay}`);
    console.log(`core_patch_site_matches=${matches.core}`);

    const patched = {
      main: patchExactlyOnce(sources.main, MAIN_PATCH_SITE, MAIN_REPLACEMENT, "main injection"),
      core: patchExactlyOnce(sources.core, CORE_PATCH_SITE, CORE_REPLACEMENT, "core injection"),
      overlay: patchExactlyOnce(sources.overlay, OVERLAY_PATCH_SITE, OVERLAY_REPLACEMENT, "overlay injection"),
    };
    assertPatchedStaticContract(patched);

    await writeAndCheckPatchedCopies(tempRoot, patched);
    console.log("temp_patched_js_syntax=PASS");
    console.log("native_single_atlas_fallback=PASS");
    console.log("dual_atlas_source_branch=PASS");

    const after = await captureFingerprint();
    assertOriginalIntegrity(before, after);
    console.log("original_integrity=PASS");
    console.log("app_asar_hash_unchanged=true");
  } finally {
    if (tempRoot !== null) {
      await fsp.rm(tempRoot, { recursive: true, force: true });
      cleanupResult = fs.existsSync(tempRoot) ? "FAIL" : "PASS";
    }
    console.log(`temp_cleanup=${cleanupResult}`);
  }
  if (cleanupResult === "FAIL") throw new Error("Temporary dry-run directory was not removed");
  console.log("verdict=BUILD_8881_DUAL_ATLAS_DRY_RUN_PASS");
}

run().catch((error) => {
  console.error(`verdict=BLOCKED`);
  console.error(`error=${error.message}`);
  process.exitCode = 1;
});
