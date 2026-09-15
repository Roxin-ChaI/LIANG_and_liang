/** Phase 3F: fingerprint-gated structural injection into temporary JS copies.
 *
 * The injected branches are parsed and statically asserted, never imported or
 * executed. The reference simulation below uses only project-owned modules.
 */
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import fsp from "node:fs/promises";
import os from "node:os";
import path from "node:path";

import {
  EXPECTED, CHUNKS, MAIN_RESULT, SOURCE, STATE_TABLE, COMPLETION, OWNER,
  FORM_COMMIT, SIBLING, ROOT_CLIP, appFingerprint, extractCurrentChunks,
  gate, locate, sha, one, count,
} from "./build-9275-locator.mjs";
import { createDualFormSourceRegistry } from "./dual-form-source.mjs";
import { loadTransitionAssets } from "./transition-assets.mjs";
import { renderTransitionOverlay } from "./transition-overlay.mjs";
import { createTransitionPlayer } from "./transition-player.mjs";

const PET_ID = "custom:liang-no-henshin";
const REQUIRED = Object.freeze(["main", "core", "overlay"]);
const CORE_ENTRY = "function Ulo(e,t){let n=Xlo[e];";
const CORE_TIMER_END = "a=null;return}i=n,e.style.backgroundPosition=Glo(Wlo(r,i),d),o()";
const NORMAL_STYLE = "style:{...Xa(rn.width),height:rn.height}";
const OWNER_TASK = "state:vt.mascotState";

// Self-contained sketch injected only into the temporary overlay copy.
// All source URLs and standalone oversized frame URLs must already be loaded;
// it has no filesystem or network path. A later real patch needs reactive
// wiring and viewport-edge verification before this branch may be installed.
const OVERLAY_HELPER = String.raw`
const __liang9275Runtime=(()=>{
  const layouts={gu_to_feng:{width:224,height:240,left:-16,top:-18},feng_to_gu:{width:208,height:224,left:-9,top:-14}};
  let forms={},sequences={},s={currentForm:"gu",targetForm:"gu",transitionId:null,operationToken:0,playbackEpoch:0,frameIndex:0,elapsedMs:0,underlyingState:"idle"};
  const active=()=>s.transitionId!==null;
  function attachAvatar(avatar){if(!avatar?.dualFormSources)return;forms=avatar.dualFormSources;sequences=avatar.transitionFrames??sequences}
  function updateUnderlyingState(next){if(typeof next==="string")s.underlyingState=next;return next}
  function commit(target){s={...s,currentForm:target,targetForm:target,transitionId:null,frameIndex:0,elapsedMs:0,playbackEpoch:s.playbackEpoch+1}}
  function requestTargetForm(target,reducedMotion=false){
    if(target!=="gu"&&target!=="feng")return false;
    if(active()&&target===s.targetForm)return true;
    if(active()){s={...s,operationToken:s.operationToken+1,targetForm:s.currentForm,transitionId:null,frameIndex:0,elapsedMs:0};if(target===s.currentForm)return true}
    if(target===s.currentForm)return true;
    if(!forms[target])return false;
    const id=s.currentForm+"_to_"+target,frames=sequences[id]?.frames;
    if(reducedMotion||!Array.isArray(frames)||frames.length==0){commit(target);return true}
    s={...s,targetForm:target,transitionId:id,operationToken:s.operationToken+1,frameIndex:0,elapsedMs:0};return true
  }
  function complete(token){
    if(!active()||token!==s.operationToken)return false;
    const sequence=sequences[s.transitionId],duration=sequence?.frameDurationMs??140;
    if(s.elapsedMs<sequence.frames.length*duration)return false;
    commit(s.targetForm);return true
  }
  function advance(ms){if(!active()||!Number.isFinite(ms)||ms<0)return false;
    const sequence=sequences[s.transitionId],duration=sequence?.frameDurationMs??140,total=sequence.frames.length*duration;
    s.elapsedMs=Math.min(total,s.elapsedMs+ms);
    if(s.elapsedMs===total)return complete(s.operationToken);
    s.frameIndex=Math.floor(s.elapsedMs/duration);return true
  }
  function hotSource(native){const atlas=forms[s.currentForm];return atlas?{...native,spritesheetUrl:atlas,spriteRowCount:11}:native}
  function sibling(normal,jsx,jsxs,Fragment,layout){
    if(!active())return normal;
    const geometry=layouts[s.transitionId],src=sequences[s.transitionId]?.frames?.[s.frameIndex];
    if(!geometry||!src)return normal;
    const mascot=layout?.mascot??{},left=(mascot.left??0)+geometry.left,top=(mascot.top??0)+geometry.top;
    const image=jsx("img",{src,alt:"",style:{position:"absolute",pointerEvents:"none",left,top,width:geometry.width,height:geometry.height,imageRendering:"pixelated"}});
    return jsxs(Fragment,{children:[normal,image]})
  }
  return{attachAvatar,updateUnderlyingState,requestTargetForm,complete,advance,hotSource,sibling,active,get state(){return s}}
})();
globalThis.__liang9275Runtime=__liang9275Runtime;
`;

const MAIN_HELPER = String.raw`
function __liang9275DualSource(result){
  if(!result?.dualFormSources?.gu||!result?.dualFormSources?.feng)return result;
  return {...result,dualFormSources:Object.freeze({...result.dualFormSources}),transitionFrames:result.transitionFrames??{}};
}
`;
const CORE_HELPER = String.raw`
function __liang9275TransitionDescriptor(request){
  if(!Array.isArray(request.frames)||!Number.isInteger(request.frameDurationMs)||request.frameDurationMs<=0)throw TypeError("invalid transition descriptor");
  return{frames:request.frames.map(frameSource=>({rowIndex:0,columnIndex:0,frameSource,frameDurationMs:request.frameDurationMs})),loopStartIndex:null,operationToken:request.operationToken};
}
`;

function replaceOne(source, needle, replacement, label) {
  one(source, needle, label);
  return source.replace(needle, replacement);
}

function patchMain(original) {
  const wrapped = replaceOne(original, MAIN_RESULT,
    MAIN_RESULT.replace("})}", "}).then(__liang9275DualSource)}"), "dual-form main result");
  return `${MAIN_HELPER}${wrapped}`;
}

function patchCore(original) {
  one(original, STATE_TABLE, "native nine-state map");
  one(original, COMPLETION, "native completion descriptor");
  let result = replaceOne(original, CORE_ENTRY,
    "function Ulo(e,t){if(e?.kind===\"liang-transition\")return __liang9275TransitionDescriptor(e);let n=Xlo[e];",
    "one-shot descriptor entry");
  result = replaceOne(result, CORE_TIMER_END,
    "a=null;if(u?.kind===\"liang-transition\")globalThis.__liang9275Runtime?.complete(u.operationToken);return}i=n,e.style.backgroundPosition=Glo(Wlo(r,i),d),o()",
    "one-shot timer completion");
  return `${CORE_HELPER}${result}`;
}

function patchOverlay(original) {
  one(original, OWNER, "overlay owner");
  one(original, FORM_COMMIT, "form-commit owner");
  one(original, ROOT_CLIP, "root clipping boundary");
  let result = replaceOne(original, OWNER,
    "function kd(){/* __liang9275TransitionOwner: task state remains native */",
    "overlay selected owner");
  result = replaceOne(result, FORM_COMMIT,
    `${FORM_COMMIT.slice(0, -1)}(__liang9275Runtime.attachAvatar(e.selectedAvatar),e)`,
    "overlay form-commit owner");
  result = replaceOne(result, SOURCE, "source:__liang9275Runtime.hotSource(Kr(c))",
    "preloaded hot source");
  result = replaceOne(result, OWNER_TASK,
    "state:__liang9275Runtime.updateUnderlyingState(vt.mascotState)",
    "underlying task state");
  result = replaceOne(result, NORMAL_STYLE,
    "style:{...Xa(rn.width),height:rn.height,opacity:__liang9275Runtime.active()?0:1}",
    "normal visual suppression, not hitbox removal");
  result = replaceOne(result, SIBLING,
    "_=(0,Lu.jsx)($l,{...n,layout:c}),_=__liang9275Runtime.sibling(_,Lu.jsx,Lu.jsxs,Lu.Fragment,c),t[10]=n,t[11]=c,t[12]=_",
    "clipping-safe layout sibling");
  return `${OVERLAY_HELPER}${result}`;
}

function staticAssertions(original, patched) {
  // Native map, 16 look rows, one-atlas loader call, clipping and interaction
  // boundaries must not be replaced or widened by the prototype branches.
  assert.equal(count(patched.core, STATE_TABLE), 1);
  assert.equal(count(patched.core, "requiredFramesByRow:[6,8,8,4,5,8,6,6,6,8,8]"), 1);
  assert.equal(count(patched.core, "rowIndex:cuo+Math.floor(o/luo)"), 1);
  assert.equal(count(patched.core, COMPLETION), 1);
  assert.equal(count(patched.main, "n.Mt({appServerClient:this.executionHostRegistry.get(),avatarId:e,preferWsl:!!process.env.WSL_DISTRO_NAME})"), 1);
  assert.ok(patched.main.includes("__liang9275DualSource"));
  assert.ok(patched.overlay.includes("hotSource(Kr(c))"));
  assert.ok(patched.core.includes("__liang9275TransitionDescriptor(e)"));
  assert.ok(patched.core.includes("__liang9275Runtime?.complete(u.operationToken)"));
  assert.ok(patched.overlay.includes("token!==s.operationToken"));
  assert.ok(patched.overlay.includes("__liang9275Runtime.sibling"));
  assert.ok(patched.overlay.includes('pointerEvents:"none"'));
  assert.ok(patched.overlay.includes("playbackEpoch:s.playbackEpoch+1"));
  assert.equal(count(patched.overlay, ROOT_CLIP), 1);
  for (const preserved of [
    '"data-avatar-overlay-hit-region":Pt===`hidden`?void 0:`mascot`',
    "style:{height:rn.height,left:rn.left,top:rn.top,width:rn.width,y:bn}",
  ]) {
    assert.equal(count(original.overlay, preserved), 1);
    assert.equal(count(patched.overlay, preserved), 1);
  }
  assert.equal(count(patched.overlay, "overflow-hidden"), count(original.overlay, "overflow-hidden"));
  assert.equal(count(patched.overlay, "function kd(){"), 1);
  assert.equal(count(patched.overlay,
    "function Nd(e){let t=(0,of.c)(43),{selectedAvatar:n,selectedAvatarId:r}="), 1);
  return "PASS";
}

function sourceRegistry() {
  return createDualFormSourceRegistry({
    mode: "dual-form", native: { petId: PET_ID },
    forms: {
      gu: { spritesheetPath: "assets/builds/gu/spritesheet.webp", spritesheetDataUrl: "data:image/webp;base64,GU" },
      feng: { spritesheetPath: "assets/builds/feng/spritesheet.webp", spritesheetDataUrl: "data:image/webp;base64,FENG" },
    },
  });
}

async function referenceSimulation() {
  const assets = await loadTransitionAssets();
  const registry = sourceRegistry();
  for (const [initial, target, countFrames] of [["gu", "feng", 10], ["feng", "gu", 8]]) {
    const player = createTransitionPlayer({ registry, assets, initialForm: initial });
    player.requestTargetForm(target);
    for (let index = 0; index < countFrames; index += 1) {
      const plan = renderTransitionOverlay(player.snapshot());
      assert.equal(plan.overlay.frameIndex, index);
      assert.deepEqual([plan.normal.width, plan.normal.height, plan.overlay.style.pointerEvents], [192, 208, "none"]);
      player.advance(140);
    }
    assert.deepEqual([player.snapshot().currentForm, player.snapshot().visualMode], [target, "NORMAL"]);
    assert.equal(renderTransitionOverlay(player.snapshot()).overlay, null);
  }
  const reversed = createTransitionPlayer({ registry, assets });
  const stale = reversed.requestTargetForm("feng").operationToken;
  reversed.advance(280);
  reversed.requestTargetForm("gu");
  assert.equal(reversed.complete(stale).stale, true);
  assert.deepEqual([reversed.snapshot().currentForm, reversed.snapshot().playbackEpoch], ["gu", 0]);
  return "PASS";
}

async function verifyOriginal(before, initialChunkHashes) {
  const after = await appFingerprint();
  gate(after, ["version", "build", "asar"], "post-run app");
  for (const property of ["size", "mode", "mtimeMs"]) {
    if (before[property] !== after[property]) throw Error(`real ASAR ${property} changed`);
  }
  const afterChunks = extractCurrentChunks();
  for (const name of Object.keys(CHUNKS)) {
    if (sha(afterChunks[name]) !== initialChunkHashes[name]) throw Error(`real ${name} chunk changed`);
  }
  return "PASS";
}

async function run() {
  let tempRoot = null;
  let cleaned = "NOT_REQUIRED";
  try {
    const before = await appFingerprint();
    gate(before, ["version", "build", "asar"], "app");
    const chunks = extractCurrentChunks();
    const hashes = Object.fromEntries(Object.entries(chunks).map(([name, data]) => [name, sha(data)]));
    gate(hashes, Object.keys(CHUNKS), "chunks");
    console.log(`fingerprint=PASS build=${before.build} app_asar_sha256=${before.asar}`);
    const original = Object.fromEntries(Object.keys(chunks).map(name => [name, chunks[name].toString("utf8")]));
    const hits = locate(original);
    for (const [name, hit] of Object.entries(hits)) console.log(`${name}_locator_count=${hit.matches}`);
    tempRoot = await fsp.mkdtemp(path.join(os.tmpdir(), "liang-build-9275-transition-"));
    const patched = {
      main: patchMain(original.main),
      core: patchCore(original.core),
      overlay: patchOverlay(original.overlay),
    };
    for (const name of REQUIRED) {
      await fsp.writeFile(path.join(tempRoot, `${name}.original.mjs`), chunks[name]);
      await fsp.writeFile(path.join(tempRoot, `${name}.patched.mjs`), patched[name]);
    }
    console.log(`temp_extracted_chunk_count=${REQUIRED.length}`);
    console.log(`static_assertions=${staticAssertions(original, patched)}`);
    for (const name of REQUIRED) {
      try {
        execFileSync(process.execPath, ["--check", path.join(tempRoot, `${name}.patched.mjs`)], {
          stdio: "pipe", maxBuffer: 16 * 1024 * 1024,
        });
      } catch (error) {
        const parser = "const fs=require('fs'),vm=require('vm');try{new vm.SourceTextModule(fs.readFileSync(process.argv[1],'utf8'))}catch(e){console.error(e.name+': '+e.message);process.exit(1)}";
        let cause = "node --check rejected temporary module";
        try {
          execFileSync(process.execPath, ["--experimental-vm-modules", "-e", parser,
            path.join(tempRoot, `${name}.patched.mjs`)], { stdio: "pipe" });
        } catch (parseError) {
          cause = String(parseError.stderr ?? "").trim().split("\n")[0] || cause;
        }
        throw Error(`${name} temp JS syntax failed: ${cause}`);
      }
      console.log(`${name}_temp_js_syntax=PASS`);
    }
    console.log(`reference_simulation=${await referenceSimulation()}`);
    console.log(`original_integrity=${await verifyOriginal(before, hashes)}`);
  } finally {
    if (tempRoot !== null) {
      await fsp.rm(tempRoot, { recursive: true, force: true });
      cleaned = fs.existsSync(tempRoot) ? "FAIL" : "PASS";
    }
    console.log(`temp_cleanup=${cleaned}`);
  }
  if (cleaned === "FAIL") throw Error("proprietary temp copies were not removed");
  console.log("verdict=BUILD_9275_TRANSITION_DRY_PATCH_PASS");
}

run().catch(error => {
  console.error(`verdict=BLOCKED error=${error.message}`);
  process.exitCode = 1;
});
