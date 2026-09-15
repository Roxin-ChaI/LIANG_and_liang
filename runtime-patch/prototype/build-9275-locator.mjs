/** Build 9275 read-only fingerprint gate and composite Pet patch-site locator.
 *
 * No proprietary JS is retained: original/marker copies exist only in one
 * mkdtemp directory, which is removed in the finally block. Real ASAR and
 * installed App are never written.
 */

import { execFileSync } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import fsp from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const APP = "/Applications/ChatGPT.app";
const PLIST = path.join(APP, "Contents/Info.plist");
const ASAR = path.join(APP, "Contents/Resources/app.asar");

const EXPECTED = Object.freeze({
  version: "26.908.70816",
  build: "9275",
  asar: "100b3a06768326eec58ae32e54fa7b85368fef8d4ead5a5866ecb0e8751bdeaa",
  preload: "9dba229e0b3cfa1cc9a7e78925b5f168b7f7385e1c18d785d13ce8e823e65207",
  main: "0765260be74e8843630d5a92e30bca574783892688e67180c119a5c58679bb61",
  loader: "a42da38cbb14b28399f1d54fcf453bffc5e9802663e7e098f187c8378f4c7a40",
  core: "5dcf4a29db25b086f9bd11d053eec60cf0c50bfd988494969cec452e03f19245",
  overlay: "51c369ad2dc365550b463e3cb119da97d94c2ffc98e01a9f18b53287d920f0cf",
  mascot: "adb931faef70d16b02e9099e973563ae5a5d38a2c316770e22d116de876919fb",
  settings: "b5a75703f92baa93703edf965ef3b2e141467934c8a67770bc69b2d873e47c55",
});

const CHUNKS = Object.freeze({
  preload: ".vite/build/preload.js",
  main: ".vite/build/main-DaMR-wdT.js",
  loader: ".vite/build/src-CCXHtyvY.js",
  core: "webview/assets/app-initial-4d7ea7f81c2d.js",
  overlay: "webview/assets/avatar-overlay-native-page-efa96d74af15.js",
  mascot: "webview/assets/avatar-mascot-button-7a295935c1d3.js",
  settings: "webview/assets/pets-settings-route-c49fd75fc38f.js",
});

// Full local shapes, not a hashed filename or isolated minified identifier.
// Every site is additionally checked against neighboring Pet-specific text.
const MAIN_RESULT = "loadAvatar(e){return n.Mt({appServerClient:this.executionHostRegistry.get(),avatarId:e,preferWsl:!!process.env.WSL_DISTRO_NAME})}";
const SOURCE = "source:Kr(c)";
const STATE_TABLE = "Xlo={failed:i4(5,8,140,240),idle:Jlo,jumping:i4(4,5,140,280),review:i4(8,6,150,280),running:i4(7,6,120,220),\"running-left\":i4(2,8,120,220),\"running-right\":i4(1,8,120,220),waving:i4(3,4,140,280),waiting:i4(6,6,150,260)}";
const COMPLETION = "loopStartIndex:r.length";
const OWNER = "function kd(){";
const FORM_COMMIT = "function Nd(e){let t=(0,of.c)(43),{selectedAvatar:n,selectedAvatarId:r}=e";
const SIBLING = "_=(0,Lu.jsx)($l,{...n,layout:c}),t[10]=n,t[11]=c,t[12]=_";
const ROOT_CLIP = "kr=Ai(`relative h-screen w-screen bg-transparent`,`overflow-hidden`";
const MARKER = "/* LIANG_PHASE_3E_TEMP_OVERLAY_LOCATOR */";

function sha(buffer) {
  return crypto.createHash("sha256").update(buffer).digest("hex");
}

async function shaFile(file) {
  const hash = crypto.createHash("sha256");
  for await (const chunk of fs.createReadStream(file)) hash.update(chunk);
  return hash.digest("hex");
}

function plistValue(key) {
  return execFileSync("/usr/libexec/PlistBuddy", ["-c", `Print :${key}`, PLIST], {
    encoding: "utf8",
  }).trim();
}

function count(source, needle) {
  let result = 0;
  let cursor = 0;
  while ((cursor = source.indexOf(needle, cursor)) !== -1) {
    result += 1;
    cursor += needle.length;
  }
  return result;
}

function one(source, needle, label) {
  const matches = count(source, needle);
  if (matches !== 1) throw Error(`${label}: expected exactly 1 match, got ${matches}`);
  return source.indexOf(needle);
}

function local(source, site, secondary, radius, label) {
  const siteIndex = one(source, site, label);
  const around = source.slice(Math.max(0, siteIndex - radius), siteIndex + site.length + radius);
  for (const needle of secondary) {
    if (!around.includes(needle)) {
      throw Error(`${label}: missing neighboring structural anchor ${needle}`);
    }
  }
  return Object.freeze({ matches: 1, contextHash: sha(source.slice(
    Math.max(0, siteIndex - 160), siteIndex + site.length + 160,
  )) });
}

function archive() {
  const fd = fs.openSync(ASAR, "r");
  try {
    const prefix = Buffer.alloc(8);
    if (fs.readSync(fd, prefix, 0, 8, 0) !== 8) throw Error("ASAR prefix truncated");
    const headerSize = prefix.readUInt32LE(4);
    const headerBuffer = Buffer.alloc(headerSize);
    if (fs.readSync(fd, headerBuffer, 0, headerSize, 8) !== headerSize) {
      throw Error("ASAR header truncated");
    }
    const jsonLength = headerBuffer.readUInt32LE(4);
    const header = JSON.parse(headerBuffer.toString("utf8", 8, 8 + jsonLength));
    return { fd, header, dataOffset: 8 + headerSize };
  } catch (error) {
    fs.closeSync(fd);
    throw error;
  }
}

function extractCurrentChunks() {
  const asar = archive();
  try {
    return Object.fromEntries(Object.entries(CHUNKS).map(([name, archivePath]) => {
      let entry = asar.header;
      for (const segment of archivePath.split("/")) entry = entry?.files?.[segment];
      if (!entry || entry.unpacked || entry.link || !Number.isSafeInteger(entry.size)
          || !/^\d+$/.test(entry.offset)) {
        throw Error(`packed current chunk absent: ${archivePath}`);
      }
      const data = Buffer.alloc(entry.size);
      const bytes = fs.readSync(
        asar.fd, data, 0, entry.size, asar.dataOffset + Number(entry.offset),
      );
      if (bytes !== entry.size) throw Error(`packed chunk truncated: ${archivePath}`);
      return [name, data];
    }));
  } finally {
    fs.closeSync(asar.fd);
  }
}

async function appFingerprint() {
  const stat = await fsp.stat(ASAR);
  return Object.freeze({
    version: plistValue("CFBundleShortVersionString"),
    build: plistValue("CFBundleVersion"),
    asar: await shaFile(ASAR),
    size: stat.size, mode: stat.mode, mtimeMs: stat.mtimeMs,
  });
}

function gate(observed, keys, stage) {
  for (const key of keys) {
    if (observed[key] !== EXPECTED[key]) {
      throw Error(`BUILD_9275_FINGERPRINT_MISMATCH ${stage} ${key}: ${observed[key]}`);
    }
  }
}

function locate(sources) {
  const hits = {
    dualForm: local(sources.main, MAIN_RESULT,
      ["petInstallManager", "load(){return n.Nt(", "previewPetInstall", "executionHostRegistry"], 600,
      "main custom-avatar result"),
    hotSwitch: local(sources.overlay, SOURCE,
      ["state:vt.mascotState", "transientState:h", "lookFrame:Dn"], 280,
      "overlay selected source"),
    descriptor: local(sources.core, STATE_TABLE,
      ["Codex pet animation frame is out of range", "frameDurationMs", "rowIndex"], 1200,
      "core named-state descriptor"),
    completion: local(sources.core, COMPLETION,
      ["function Ulo(", "window.setTimeout", "Codex pet animation frame is out of range"], 2300,
      "core completion/timing"),
    owner: local(sources.overlay, OWNER,
      ["selectedAvatarId", "startsWith(`custom:`)", "selectedAvatar:"], 950,
      "overlay selected-avatar owner"),
    formCommit: local(sources.overlay, FORM_COMMIT,
      ["selectedAvatarId", "selectedAvatar", "petVisible"], 850,
      "overlay form-commit owner"),
    sibling: local(sources.overlay, SIBLING,
      ["function Nu(e)", "layout$", "quickChatFocusPreparation"], 1600,
      "transition sibling layout wrapper"),
    clipping: local(sources.overlay, ROOT_CLIP,
      ["data-avatar-overlay-content-frame", "overflow-hidden", "className:kr"], 9000,
      "clipping-safe root boundary"),
  };

  // The normal hitbox must stay in the mascot subtree; the new visual-only
  // layer belongs at Nu, outside $l's clipping <main>.
  one(sources.overlay,
    '"data-avatar-overlay-hit-region":Pt===`hidden`?void 0:`mascot`',
    "normal mascot hit region");
  one(sources.overlay,
    "style:{height:rn.height,left:rn.left,top:rn.top,width:rn.width,y:bn}",
    "normal absolute mascot box");
  one(sources.overlay, "(0,Q.jsx)(`main`,{\"aria-hidden\":Er,className:kr",
    "clipping overlay main");
  one(sources.overlay, "(0,Lu.jsx)($l,{...n,layout:c})",
    "layout wrapper root render");
  if (sources.overlay.indexOf("function Nu(e)") <= sources.overlay.indexOf("function $l(e)")) {
    throw Error("CLIPPING_ARCHITECTURE_BLOCKED layout wrapper must be outside clipped root");
  }
  if (sources.overlay.includes(MARKER)) throw Error("temporary marker already exists in original");
  return Object.freeze(hits);
}

async function writeTempCopies(tempRoot, chunks) {
  for (const [name, buffer] of Object.entries(chunks)) {
    await fsp.writeFile(path.join(tempRoot, `${name}.original.js`), buffer);
  }
}

async function run() {
  let tempRoot = null;
  let cleanup = "NOT_REQUIRED";
  try {
    // Gate BEFORE extraction or locator, unlike the historical 8881 script.
    const before = await appFingerprint();
    gate(before, ["version", "build", "asar"], "app");
    const chunks = extractCurrentChunks();
    const chunkHashes = Object.fromEntries(Object.entries(chunks).map(([name, data]) => [name, sha(data)]));
    gate(chunkHashes, Object.keys(CHUNKS), "chunks");
    console.log("build_9275_fingerprint=PASS");
    console.log(`version=${before.version} build=${before.build} app_asar_sha256=${before.asar}`);

    tempRoot = await fsp.mkdtemp(path.join(os.tmpdir(), "liang-build-9275-locator-"));
    await writeTempCopies(tempRoot, chunks);
    const sources = Object.fromEntries(Object.keys(chunks).map(name => [name, chunks[name].toString("utf8")]));
    const hits = locate(sources);
    for (const [name, hit] of Object.entries(hits)) {
      console.log(`${name}_locator_count=${hit.matches} context_sha256=${hit.contextHash}`);
    }
    console.log("clipping_safe_insertion=CLIPPING_SAFE_INSERTION_FOUND");
    console.log("normal_mascot_box_and_hit_region=PRESERVED");

    const patched = sources.overlay.replace(SIBLING, `${MARKER}${SIBLING}`);
    if (count(patched, MARKER) !== 1 || patched.replace(MARKER, "") !== sources.overlay) {
      throw Error("temporary marker was not applied exactly once or original branch changed");
    }
    const tempPatched = path.join(tempRoot, "overlay.marker.mjs");
    await fsp.writeFile(tempPatched, patched);
    execFileSync(process.execPath, ["--check", tempPatched], { stdio: "pipe" });
    console.log("temp_modified_js_syntax=PASS marker_count=1 original_branch_preserved=true");

    const after = await appFingerprint();
    gate(after, ["version", "build", "asar"], "post-run app");
    for (const key of ["size", "mode", "mtimeMs"]) {
      if (before[key] !== after[key]) throw Error(`original ASAR integrity changed: ${key}`);
    }
    const afterChunks = extractCurrentChunks();
    for (const name of Object.keys(CHUNKS)) {
      if (sha(afterChunks[name]) !== chunkHashes[name]) {
        throw Error(`original archived chunk changed: ${name}`);
      }
    }
    console.log("original_app_asar_and_key_chunks_unchanged=true");
  } finally {
    if (tempRoot !== null) {
      await fsp.rm(tempRoot, { recursive: true, force: true });
      cleanup = fs.existsSync(tempRoot) ? "FAIL" : "PASS";
    }
    console.log(`temp_cleanup=${cleanup}`);
  }
  if (cleanup === "FAIL") throw Error("temporary proprietary copies not cleaned");
  console.log("verdict=BUILD_9275_RECON_LOCATOR_PASS");
}

export {
  EXPECTED, CHUNKS, MAIN_RESULT, SOURCE, STATE_TABLE, COMPLETION, OWNER,
  FORM_COMMIT, SIBLING, ROOT_CLIP, sha, shaFile, count, one, appFingerprint,
  extractCurrentChunks, gate, locate,
};

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  run().catch(error => {
    console.error(`verdict=BLOCKED error=${error.message}`);
    process.exitCode = 1;
  });
}
