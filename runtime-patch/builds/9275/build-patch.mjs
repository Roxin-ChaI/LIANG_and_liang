#!/usr/bin/env node
/** Deterministic Build 9275 patch recipe. Never patches input in place. */

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import fsp from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const SPEC_PATH = path.join(path.dirname(fileURLToPath(import.meta.url)), "patch-spec.json");
export const CONTEXT_NAME = ".liang-build-context.json";
const REPORT_NAME = "patch-report.json";

const DUAL_FORM_HELPER = String.raw`
async function __liang9275LoadDualForm(result){
  try{
    if(result==null||typeof result!=="object")return result;
    const petId=result.petId??result.id;if(petId!=="custom:liang-no-henshin"&&petId!=="liang-no-henshin")return result;
    const root=result.directoryPath;if(typeof root!=="string")return result;
    const fs=require("node:fs/promises"),path=require("node:path"),realRoot=await fs.realpath(root);
    const inside=async relative=>{if(typeof relative!=="string"||relative.includes("\\")||relative.split("/").some(part=>part===""||part==="."||part==="..")||path.isAbsolute(relative))throw Error("unsafe Liang asset path");const candidate=await fs.realpath(path.resolve(realRoot,relative));if(!candidate.startsWith(realRoot+path.sep))throw Error("Liang asset path escape");return candidate};
    const sidecar=JSON.parse(await fs.readFile(await inside("liang-runtime.json"),"utf8"));
    if(sidecar.schemaVersion!==1||sidecar.initialForm!=="gu")return result;
    const forms={};for(const form of ["gu","feng"]){const relative=sidecar.forms?.[form]?.spritesheetPath,file=await inside(relative),bytes=await fs.readFile(file);forms[form]="data:image/webp;base64,"+bytes.toString("base64")}
    const transitions={};for(const name of ["gu_to_feng","feng_to_gu"]){const source=sidecar.transitions?.[name];if(!source||!Array.isArray(source.frames)||!Number.isInteger(source.frameDurationMs)||source.frameDurationMs<=0)throw Error("invalid Liang transition");const frames=[];for(const relative of source.frames)frames.push("data:image/png;base64,"+(await fs.readFile(await inside(relative))).toString("base64"));transitions[name]={...source,frames}}
    return{...result,dualFormSources:Object.freeze(forms),runtimeInitialForm:sidecar.initialForm,transitionFrames:Object.freeze(transitions)}
  }catch(_error){return result}
}
`;

const TRANSITION_DESCRIPTOR_HELPER = String.raw`
function __liang9275TransitionDescriptor(request){
  if(!Array.isArray(request.frames)||!Number.isInteger(request.frameDurationMs)||request.frameDurationMs<=0)throw TypeError("invalid transition descriptor");
  return{frames:request.frames.map(frameSource=>({rowIndex:0,columnIndex:0,frameSource,frameDurationMs:request.frameDurationMs})),loopStartIndex:null,operationToken:request.operationToken}
}
`;

const TRANSITION_RUNTIME_HELPER = String.raw`
const __liang9275Runtime=(()=>{
  let forms={},sequences={},layouts={},s={currentForm:"gu",targetForm:"gu",transitionId:null,operationToken:0,playbackEpoch:0,frameIndex:0,elapsedMs:0,underlyingState:"idle"};
  const active=()=>s.transitionId!==null;
  function attachAvatar(avatar){if(!avatar?.dualFormSources)return;forms=avatar.dualFormSources;sequences=avatar.transitionFrames??{};layouts=Object.fromEntries(Object.entries(sequences).map(([name,value])=>[name,value.layout??{}]))}
  function updateUnderlyingState(next){if(typeof next==="string")s.underlyingState=next;return next}
  function commit(target){s={...s,currentForm:target,targetForm:target,transitionId:null,frameIndex:0,elapsedMs:0,playbackEpoch:s.playbackEpoch+1}}
  function requestTargetForm(target,reducedMotion=false){
    if(target!=="gu"&&target!=="feng")return false;if(active()&&target===s.targetForm)return true;
    if(active()){s={...s,operationToken:s.operationToken+1,targetForm:s.currentForm,transitionId:null,frameIndex:0,elapsedMs:0};if(target===s.currentForm)return true}
    if(target===s.currentForm)return true;if(!forms[target])return false;const id=s.currentForm+"_to_"+target,sequence=sequences[id];
    if(reducedMotion||!Array.isArray(sequence?.frames)||sequence.frames.length===0){commit(target);return true}
    s={...s,targetForm:target,transitionId:id,operationToken:s.operationToken+1,frameIndex:0,elapsedMs:0};return true
  }
  function complete(token){if(!active()||token!==s.operationToken)return false;const sequence=sequences[s.transitionId],duration=sequence?.frameDurationMs??140;if(s.elapsedMs<sequence.frames.length*duration)return false;commit(s.targetForm);return true}
  function advance(ms){if(!active()||!Number.isFinite(ms)||ms<0)return false;const sequence=sequences[s.transitionId],duration=sequence.frameDurationMs??140,total=sequence.frames.length*duration;s.elapsedMs=Math.min(total,s.elapsedMs+ms);if(s.elapsedMs===total)return complete(s.operationToken);s.frameIndex=Math.floor(s.elapsedMs/duration);return true}
  function hotSource(native){const atlas=forms[s.currentForm];return atlas?{...native,spritesheetUrl:atlas,spriteRowCount:11,key:(native?.key??"liang")+"-"+s.playbackEpoch}:native}
  function sibling(normal,jsx,jsxs,Fragment,layout){if(!active())return normal;const geometry=layouts[s.transitionId],src=sequences[s.transitionId]?.frames?.[s.frameIndex];if(!geometry||!src)return normal;const mascot=layout?.mascot??{},left=(mascot.left??0)+(geometry.offsetLeft??0),top=(mascot.top??0)+(geometry.offsetTop??0),image=jsx("img",{src,alt:"",style:{position:"absolute",pointerEvents:"none",left,top,width:geometry.canvasWidth,height:geometry.canvasHeight,imageRendering:"pixelated"}});return jsxs(Fragment,{children:[normal,image]})}
  return{attachAvatar,updateUnderlyingState,requestTargetForm,complete,advance,hotSource,sibling,active,get state(){return s}}
})();globalThis.__liang9275Runtime=__liang9275Runtime;
`;

const BRIDGE_MAIN_HELPER = String.raw`
const __liang9275IpcRequest="liang-no-henshin:set-target-form",__liang9275IpcResponse="liang-no-henshin:set-target-form-response";let __liang9275Bridge=null;
function __liang9275SocketPath(){const os=require("node:os"),path=require("node:path"),uid=typeof process.getuid==="function"?process.getuid():process.pid;return path.join(os.tmpdir(),"liang-no-henshin-"+uid,"runtime.sock")}
function __liang9275CreateBridgeServer({socketPath,dispatch}){const net=require("node:net"),fs=require("node:fs"),path=require("node:path");let server=null;return{async start(){fs.mkdirSync(path.dirname(socketPath),{recursive:true,mode:448});try{const stat=fs.lstatSync(socketPath);if(!stat.isSocket()||stat.uid!==process.getuid())throw Error("unsafe Liang socket");fs.unlinkSync(socketPath)}catch(error){if(error.code!=="ENOENT")throw error}server=net.createServer(client=>{let wire="";client.setEncoding("utf8");client.on("data",async chunk=>{wire+=chunk;if(wire.length>4096){client.destroy();return}const end=wire.indexOf("\n");if(end<0)return;let request;try{request=JSON.parse(wire.slice(0,end));if(request.protocolVersion!==1||request.method!=="setTargetForm")throw Error("invalid request");const result=await dispatch({requestId:request.requestId,target:request.params?.target,animate:request.params?.animate});client.end(JSON.stringify({protocolVersion:1,requestId:request.requestId,ok:true,result})+"\n")}catch(error){client.end(JSON.stringify({protocolVersion:1,requestId:request?.requestId??"invalid",ok:false,error:{code:error.code??"INVALID_REQUEST",message:"request rejected"}})+"\n")}})});await new Promise((resolve,reject)=>{server.once("error",reject);server.listen(socketPath,()=>{server.off("error",reject);fs.chmodSync(socketPath,384);resolve()})})},async stop(){if(server)await new Promise(resolve=>server.close(resolve));try{fs.unlinkSync(socketPath)}catch(error){if(error.code!=="ENOENT")throw error}}}}
function __liang9275InstallBridge({app,ipcMain,avatarOverlayManager}){const pending=new Map,dispatch=command=>new Promise((resolve,reject)=>{const sender=avatarOverlayManager.getVisibleWebContents();if(sender==null||sender.isDestroyed()){const error=Error("runtime not ready");error.code="RUNTIME_NOT_READY";reject(error);return}const timer=setTimeout(()=>{pending.delete(command.requestId);const error=Error("runtime response timeout");error.code="RUNTIME_TIMEOUT";reject(error)},2000);pending.set(command.requestId,{resolve,reject,timer,sender});sender.send(__liang9275IpcRequest,command)});ipcMain.on(__liang9275IpcResponse,(event,payload)=>{const item=payload&&typeof payload.requestId==="string"?pending.get(payload.requestId):null;if(!item||event.sender!==item.sender)return;pending.delete(payload.requestId);clearTimeout(item.timer);payload.ok?item.resolve(payload.result):item.reject(Object.assign(Error(payload.error?.message??"runtime rejected"),{code:payload.error?.code}))});app.whenReady().then(async()=>{__liang9275Bridge=__liang9275CreateBridgeServer({socketPath:__liang9275SocketPath(),dispatch});await __liang9275Bridge.start()});app.once("before-quit",()=>{for(const item of pending.values()){clearTimeout(item.timer);item.reject(Error("app shutting down"))}pending.clear();__liang9275Bridge?.stop()})}
`;

const PRELOAD_HELPER = String.raw`
const __liang9275ControlApi=Object.freeze({onSetTargetForm(callback){if(typeof callback!=="function")throw TypeError("callback required");const listener=async(_event,payload)=>{let response;try{response={ok:true,result:await callback(payload)}}catch(_error){response={ok:false,error:{code:"RUNTIME_REJECTED",message:"runtime rejected request"}}}e.ipcRenderer.send("liang-no-henshin:set-target-form-response",{requestId:payload?.requestId,...response})};e.ipcRenderer.on("liang-no-henshin:set-target-form",listener);return()=>e.ipcRenderer.off("liang-no-henshin:set-target-form",listener)}});
`;

const CONTROL_BINDING_HELPER = String.raw`
let __liang9275ControlUnsubscribe=null;function __liang9275BindControl(){if(__liang9275ControlUnsubscribe!=null)return;const api=globalThis.liangNoHenshin,binding=globalThis.__liang9275Runtime?.requestTargetForm;if(typeof api?.onSetTargetForm!=="function"||typeof binding!=="function")return;__liang9275ControlUnsubscribe=api.onSetTargetForm(async payload=>{if(payload==null||typeof payload.requestId!=="string"||(payload.target!=="gu"&&payload.target!=="feng")||typeof payload.animate!=="boolean")throw Error("invalid target-form request");const accepted=await binding.call(globalThis.__liang9275Runtime,payload.target,!payload.animate),snapshot=globalThis.__liang9275Runtime.state;return{accepted:accepted!==false,currentForm:snapshot.currentForm,targetForm:snapshot.targetForm,transitioning:snapshot.transitionId!=null}})}
`;

function sha(value) { return crypto.createHash("sha256").update(value).digest("hex"); }
async function shaFile(file) { return sha(await fsp.readFile(file)); }
function count(source, needle) { let result = 0, offset = 0; while ((offset = source.indexOf(needle, offset)) !== -1) { result += 1; offset += needle.length; } return result; }
function fail(code, message) { const error = new Error(message); error.code = code; throw error; }
function safeRelative(value) { return typeof value === "string" && value.length > 0 && !path.isAbsolute(value) && !value.includes("\\") && value.split("/").every(part => part && part !== "." && part !== ".."); }

export async function loadSpec(specPath = SPEC_PATH) {
  const spec = JSON.parse(await fsp.readFile(specPath, "utf8"));
  if (spec.formatVersion !== 1 || spec.target?.version !== "26.908.70816" || spec.target?.build !== "9275" || !/^[0-9a-f]{64}$/.test(spec.target?.appAsarSha256 ?? "")) fail("INVALID_PATCH_SPEC", "invalid Build 9275 patch spec");
  for (const [name, chunk] of Object.entries(spec.chunks ?? {})) if (!safeRelative(chunk.path) || !/^[0-9a-f]{64}$/.test(chunk.sha256 ?? "")) fail("INVALID_PATCH_SPEC", `invalid chunk ${name}`);
  const ids = spec.operations?.map(operation => operation.id) ?? [];
  if (ids.length !== new Set(ids).size || ids.length < 10) fail("INVALID_PATCH_SPEC", "patch operation IDs are incomplete");
  return spec;
}

function replaceOne(source, needle, replacement, label) {
  const matches = count(source, needle); if (matches !== 1) fail("LOCATOR_MATCH_COUNT", `${label}: expected exactly 1 match, got ${matches}`); return source.replace(needle, replacement);
}

const OPERATION_APPLIERS = Object.freeze({
  "dual-form-loader-model": (s, n) => `${DUAL_FORM_HELPER}${replaceOne(s, n, n.replace("})}", "}).then(__liang9275LoadDualForm)}"), "dual loader")}`,
  "source-hot-switch": (s, n) => replaceOne(s, n, "source:__liang9275Runtime.hotSource(Kr(c))", "hot source"),
  "transition-descriptor": (s, n) => `${TRANSITION_DESCRIPTOR_HELPER}${replaceOne(s, n, 'function Ulo(e,t){if(e?.kind==="liang-transition")return __liang9275TransitionDescriptor(e);let n=Xlo[e];', "descriptor")}`,
  "transition-completion": (s, n) => replaceOne(s, n, 'a=null;if(u?.kind==="liang-transition")globalThis.__liang9275Runtime?.complete(u.operationToken);return}i=n,e.style.backgroundPosition=Glo(Wlo(r,i),d),o()', "completion"),
  "oversized-sibling-overlay": (s, n) => replaceOne(s, n, '_=(0,Lu.jsx)($l,{...n,layout:c}),_=__liang9275Runtime.sibling(_,Lu.jsx,Lu.jsxs,Lu.Fragment,c),t[10]=n,t[11]=c,t[12]=_', "sibling"),
  "operation-token-guard": (s, n) => replaceOne(s, n, `${TRANSITION_RUNTIME_HELPER}${n}`, "runtime owner"),
  "local-control-bridge-main": (s, n) => `${BRIDGE_MAIN_HELPER}${replaceOne(s, n, 'H=new wle(V,d,S),__liang9275InstallBridge({app:l.app,ipcMain:l.ipcMain,avatarOverlayManager:H}),ee=o4e', "main bridge")}`,
  "preload-typed-event": (s, n) => `${PRELOAD_HELPER}${replaceOne(s, n, 'e.contextBridge.exposeInMainWorld(`electronBridge`,R),e.contextBridge.exposeInMainWorld(`liangNoHenshin`,__liang9275ControlApi),typeof window<`u`', "preload")}`,
  "request-target-form-binding": (s, n) => `${CONTROL_BINDING_HELPER}${replaceOne(s, n, n, "control binding")}`,
  "overlay-event-subscription": (s, n) => replaceOne(s, n, `${n};__liang9275Runtime.attachAvatar(e.selectedAvatar);__liang9275BindControl()`, "control subscription"),
  "transition-underlying-state": (s, n) => replaceOne(s, n, "state:__liang9275Runtime.updateUnderlyingState(vt.mascotState)", "underlying state"),
  "transition-normal-suppression": (s, n) => replaceOne(s, n, "style:{...Xa(rn.width),height:rn.height,opacity:__liang9275Runtime.active()?0:1}", "normal suppression"),
});

async function copyInput(input, output) {
  if (fs.existsSync(output)) fail("OUTPUT_EXISTS", "output directory already exists");
  await fsp.mkdir(output, { recursive: true });
  for (const entry of await fsp.readdir(input, { withFileTypes: true })) {
    if (entry.name === CONTEXT_NAME) continue;
    await fsp.cp(path.join(input, entry.name), path.join(output, entry.name), { recursive: true, dereference: false, errorOnExist: true });
  }
}

function assertPostPatch(spec, sources) {
  const combined = Object.values(sources).join("\n");
  for (const marker of spec.postPatchAssertions) assert.ok(combined.includes(marker), `missing assertion ${marker}`);
  assert.ok(combined.includes("token!==s.operationToken"));
  assert.ok(combined.includes('"liang-no-henshin-"+uid,"runtime.sock"'));
  assert.ok(!combined.includes(".codex/ipc/ipc.sock"));
  assert.ok(combined.includes("return result") && combined.includes("catch(_error){return result}"));
}

export async function buildPatch({ inputDir, outputDir, specPath = SPEC_PATH }) {
  const input = path.resolve(inputDir), output = path.resolve(outputDir), spec = await loadSpec(specPath);
  if (input === output || output.startsWith(`${input}${path.sep}`)) fail("INPLACE_PATCH_REFUSED", "output must be a new independent directory");
  const context = JSON.parse(await fsp.readFile(path.join(input, CONTEXT_NAME), "utf8"));
  if (context.version !== spec.target.version || context.build !== spec.target.build) fail("UNSUPPORTED_BUILD", "version/build mismatch");
  if (context.appAsarSha256 !== spec.target.appAsarSha256) fail("UNSUPPORTED_BUILD", "app.asar fingerprint mismatch");
  const sources = {};
  for (const [name, chunk] of Object.entries(spec.chunks)) {
    const file = path.join(input, chunk.path); if (await shaFile(file) !== chunk.sha256) fail("UNSUPPORTED_BUILD", `chunk fingerprint mismatch: ${name}`); sources[name] = await fsp.readFile(file, "utf8");
  }
  for (const [name, locator] of Object.entries(spec.locators)) {
    const matches = count(sources[locator.target], locator.needle); if (matches !== locator.expectedMatches) fail("LOCATOR_MATCH_COUNT", `${name}: expected ${locator.expectedMatches}, got ${matches}`);
  }
  await copyInput(input, output);
  const reports = [];
  for (const operation of spec.operations) {
    const locator = spec.locators[operation.locator], apply = OPERATION_APPLIERS[operation.id];
    if (!locator || operation.target !== locator.target || typeof apply !== "function") fail("INVALID_PATCH_SPEC", `unknown operation ${operation.id}`);
    const original = sources[operation.target], patched = apply(original, locator.needle); sources[operation.target] = patched;
    reports.push({ operationId: operation.id, target: operation.target, originalSha256: sha(original), patchedSha256: sha(patched), matchCount: 1, status: "PATCHED" });
  }
  assertPostPatch(spec, sources);
  for (const target of new Set(spec.operations.map(operation => operation.target))) {
    const destination = path.join(output, spec.chunks[target].path); await fsp.writeFile(destination, sources[target]);
    execFileSync(process.execPath, ["--check", destination], { stdio: "pipe", maxBuffer: 32 * 1024 * 1024 });
  }
  const targetHashes = Object.fromEntries(await Promise.all(Object.entries(spec.chunks).map(async ([name, chunk]) => [name, await shaFile(path.join(output, chunk.path))])));
  const report = { formatVersion: 1, patchSpecVersion: spec.patchSpecVersion, target: spec.target, operations: reports, targetHashes, assertions: Object.fromEntries(spec.postPatchAssertions.map(key => [key, true])), status: "PASS" };
  await fsp.writeFile(path.join(output, REPORT_NAME), `${JSON.stringify(report, null, 2)}\n`);
  return report;
}

async function main() {
  const args = process.argv.slice(2), value = flag => { const index = args.indexOf(flag); return index < 0 ? null : args[index + 1]; };
  const inputDir = value("--input-dir"), outputDir = value("--output-dir"), specPath = value("--spec") ?? SPEC_PATH;
  if (!inputDir || !outputDir) fail("USAGE", "usage: build-patch.mjs --input-dir <dir> --output-dir <dir> [--spec <file>]");
  const report = await buildPatch({ inputDir, outputDir, specPath }); console.log(`patch_status=${report.status}`); console.log(`operations=${report.operations.length}`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main().catch(error => { console.error(`patch_error=${error.code ?? "ERROR"} message=${error.message}`); process.exitCode = 1; });
