import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test, { after, before, beforeEach } from "node:test";

import { buildPatch, CONTEXT_NAME, loadSpec, SPEC_PATH } from "./build-patch.mjs";

let root, fixtureSequence = 0;
const hash = value => crypto.createHash("sha256").update(value).digest("hex");

const sources = {
  main: 'const n={Mt(){return Promise.resolve({})}};const x={loadAvatar(e){return n.Mt({appServerClient:this.executionHostRegistry.get(),avatarId:e,preferWsl:!!process.env.WSL_DISTRO_NAME})}};H=new wle(V,d,S),ee=o4e;\n',
  preload: 'e.contextBridge.exposeInMainWorld(`electronBridge`,R),typeof window<`u`;\n',
  loader: 'export const loader=true;\n',
  core: 'const Xlo={};function Ulo(e,t){let n=Xlo[e];return n}function q(){if(x){a=null;return}i=n,e.style.backgroundPosition=Glo(Wlo(r,i),d),o()}const native={loopStartIndex:r.length};\n',
  overlay: 'function kd(){return 1}function Nd(e){let t=(0,of.c)(43),{selectedAvatar:n,selectedAvatarId:r}=e;return t}const source={source:Kr(c)};function Nu(e){let _;_=(0,Lu.jsx)($l,{...n,layout:c}),t[10]=n,t[11]=c,t[12]=_;return _}const kr=Ai(`relative h-screen w-screen bg-transparent`,`overflow-hidden`);const task={state:vt.mascotState};const normal={style:{...Xa(rn.width),height:rn.height}};\n',
  mascot: 'export const mascot=true;\n',
  settings: 'export const settings=true;\n',
};

async function fixture({ version = "26.908.70816", build = "9275", asar = "a".repeat(64), mutateSpec } = {}) {
  const id = fixtureSequence++, input = path.join(root, `input-${id}`), output = path.join(root, `output-${id}`), specPath = path.join(root, `spec-${id}.json`), production = await loadSpec();
  const spec = structuredClone(production); spec.target.appAsarSha256 = asar;
  await fs.mkdir(input, { recursive: true });
  for (const [name, chunk] of Object.entries(spec.chunks)) { const content = sources[name]; await fs.mkdir(path.dirname(path.join(input, chunk.path)), { recursive: true }); await fs.writeFile(path.join(input, chunk.path), content); chunk.sha256 = hash(content); }
  if (mutateSpec) mutateSpec(spec, input);
  await fs.writeFile(path.join(input, CONTEXT_NAME), JSON.stringify({ version, build, appAsarSha256: asar }));
  await fs.writeFile(specPath, JSON.stringify(spec)); return { input, output, specPath, spec };
}

before(async () => { root = await fs.mkdtemp(path.join(os.tmpdir(), "liang-build-patch-test-")); });
after(async () => { await fs.rm(root, { recursive: true, force: true }); });
beforeEach(() => {});

test("production spec freezes exact Build 9275 fingerprint", async () => { const spec = await loadSpec(SPEC_PATH); assert.deepEqual(spec.target, { version: "26.908.70816", build: "9275", appAsarSha256: "100b3a06768326eec58ae32e54fa7b85368fef8d4ead5a5866ecb0e8751bdeaa" }); assert.equal(Object.keys(spec.chunks).length, 7); });
test("wrong build is rejected", async () => { const f = await fixture({ build: "9276" }); await assert.rejects(buildPatch({ inputDir: f.input, outputDir: f.output, specPath: f.specPath }), error => error.code === "UNSUPPORTED_BUILD"); });
test("wrong chunk hash is rejected", async () => { const f = await fixture(); await fs.appendFile(path.join(f.input, f.spec.chunks.loader.path), "tampered"); await assert.rejects(buildPatch({ inputDir: f.input, outputDir: f.output, specPath: f.specPath }), error => error.code === "UNSUPPORTED_BUILD"); });
test("missing locator hard fails", async () => { const f = await fixture(); const file = path.join(f.input, f.spec.chunks.overlay.path); const text = (await fs.readFile(file, "utf8")).replace("source:Kr(c)", "source:Other(c)"); await fs.writeFile(file, text); f.spec.chunks.overlay.sha256 = hash(text); await fs.writeFile(f.specPath, JSON.stringify(f.spec)); await assert.rejects(buildPatch({ inputDir: f.input, outputDir: f.output, specPath: f.specPath }), error => error.code === "LOCATOR_MATCH_COUNT"); });
test("duplicate locator hard fails", async () => { const f = await fixture(); const file = path.join(f.input, f.spec.chunks.overlay.path); const text = `${await fs.readFile(file, "utf8")}const duplicate={source:Kr(c)};`; await fs.writeFile(file, text); f.spec.chunks.overlay.sha256 = hash(text); await fs.writeFile(f.specPath, JSON.stringify(f.spec)); await assert.rejects(buildPatch({ inputDir: f.input, outputDir: f.output, specPath: f.specPath }), error => error.code === "LOCATOR_MATCH_COUNT"); });
test("all frozen operations apply exactly once", async () => { const f = await fixture(); const report = await buildPatch({ inputDir: f.input, outputDir: f.output, specPath: f.specPath }); assert.equal(report.operations.length, 12); assert.ok(report.operations.every(item => item.matchCount === 1 && item.status === "PATCHED")); assert.deepEqual(report.operations.map(item => item.operationId), f.spec.operations.map(item => item.id)); });
test("patch is deterministic", async () => { const a = await fixture(), b = await fixture(); b.spec.target.appAsarSha256 = a.spec.target.appAsarSha256; await fs.writeFile(path.join(b.input, CONTEXT_NAME), JSON.stringify({ version: "26.908.70816", build: "9275", appAsarSha256: a.spec.target.appAsarSha256 })); await fs.writeFile(b.specPath, JSON.stringify(b.spec)); const one = await buildPatch({ inputDir: a.input, outputDir: a.output, specPath: a.specPath }), two = await buildPatch({ inputDir: b.input, outputDir: b.output, specPath: b.specPath }); assert.deepEqual(one.targetHashes, two.targetHashes); });
test("native fallback remains in patched main", async () => { const f = await fixture(); await buildPatch({ inputDir: f.input, outputDir: f.output, specPath: f.specPath }); const main = await fs.readFile(path.join(f.output, f.spec.chunks.main.path), "utf8"); assert.ok(main.includes("catch(_error){return result}")); assert.ok(main.includes("return n.Mt(")); });
test("private Codex ipc socket is never introduced", async () => { const f = await fixture(); await buildPatch({ inputDir: f.input, outputDir: f.output, specPath: f.specPath }); const combined = (await Promise.all(Object.values(f.spec.chunks).map(chunk => fs.readFile(path.join(f.output, chunk.path), "utf8")))).join("\n"); assert.ok(!combined.includes(".codex/ipc/ipc.sock")); });
test("dedicated bridge namespace exists", async () => { const f = await fixture(); await buildPatch({ inputDir: f.input, outputDir: f.output, specPath: f.specPath }); const main = await fs.readFile(path.join(f.output, f.spec.chunks.main.path), "utf8"); assert.ok(main.includes('"liang-no-henshin-"+uid,"runtime.sock"')); });
test("transition overlay branch exists", async () => { const f = await fixture(); await buildPatch({ inputDir: f.input, outputDir: f.output, specPath: f.specPath }); const overlay = await fs.readFile(path.join(f.output, f.spec.chunks.overlay.path), "utf8"); assert.ok(overlay.includes("__liang9275Runtime.sibling")); assert.ok(overlay.includes('pointerEvents:"none"')); });
test("stale operation token guard exists", async () => { const f = await fixture(); await buildPatch({ inputDir: f.input, outputDir: f.output, specPath: f.specPath }); const overlay = await fs.readFile(path.join(f.output, f.spec.chunks.overlay.path), "utf8"); assert.ok(overlay.includes("token!==s.operationToken")); });
