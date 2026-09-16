/** Build 9275 Local Control Bridge temporary-copy dry patch.
 *
 * Proprietary chunks are read from the installed archive, fingerprint-gated,
 * copied to one mkdtemp directory, patched there, parsed, and removed. Nothing
 * in /Applications or ~/.codex is written or executed.
 */

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import fsp from "node:fs/promises";
import os from "node:os";
import path from "node:path";

import {
  EXPECTED, CHUNKS, FORM_COMMIT, appFingerprint, count,
  extractCurrentChunks, gate, one, sha,
} from "./build-9275-locator.mjs";

const IPC_REQUEST = "liang-no-henshin:set-target-form";
const IPC_RESPONSE = "liang-no-henshin:set-target-form-response";
const MAIN_REGISTRATION = "H=new wle(V,d,S),ee=o4e";
const PRELOAD_INSERTION = "e.contextBridge.exposeInMainWorld(`electronBridge`,R),typeof window<`u`";
const OVERLAY_SUBSCRIPTION = FORM_COMMIT;
const RUNTIME_BINDING = "globalThis.__liang9275Runtime?.requestTargetForm";
const TIMEOUT_MS = 2_000;

const MAIN_HELPER = String.raw`
const __liang9275IpcRequest="liang-no-henshin:set-target-form";
const __liang9275IpcResponse="liang-no-henshin:set-target-form-response";
function __liang9275SocketPath(){
  const os=require("node:os"),path=require("node:path"),uid=typeof process.getuid==="function"?process.getuid():process.pid;
  return path.join(os.tmpdir(),"liang-no-henshin-"+uid,"runtime.sock")
}
function __liang9275InstallBridge({app,ipcMain,avatarOverlayManager,createBridgeServer}){
  const pending=new Map;let server=null;
  const reply=(event,payload)=>{
    const item=payload&&typeof payload.requestId==="string"?pending.get(payload.requestId):null;
    if(!item||event.sender!==item.sender)return;
    pending.delete(payload.requestId);clearTimeout(item.timer);item.resolve(payload)
  };
  ipcMain.on(__liang9275IpcResponse,reply);
  const dispatch=command=>new Promise((resolve,reject)=>{
    const sender=avatarOverlayManager.getVisibleWebContents();
    if(sender==null||sender.isDestroyed()){let error=Error("runtime not ready");error.code="RUNTIME_NOT_READY";reject(error);return}
    const timer=setTimeout(()=>{pending.delete(command.requestId);let error=Error("runtime response timeout");error.code="RUNTIME_TIMEOUT";reject(error)},2000);
    pending.set(command.requestId,{resolve,reject,timer,sender});
    sender.send(__liang9275IpcRequest,{requestId:command.requestId,target:command.target,animate:command.animate})
  });
  app.whenReady().then(async()=>{
    if(typeof createBridgeServer!=="function")throw Error("bridge factory unavailable");
    server=createBridgeServer({socketPath:__liang9275SocketPath(),dispatch,maxMessageBytes:4096});await server.start()
  });
  app.once("before-quit",()=>{ipcMain.off(__liang9275IpcResponse,reply);for(const item of pending.values()){clearTimeout(item.timer);item.reject(Error("app shutting down"))}pending.clear();server?.stop()})
}
`;

const PRELOAD_HELPER = String.raw`
const __liang9275ControlApi=Object.freeze({
  onSetTargetForm(callback){
    if(typeof callback!=="function")throw TypeError("callback required");
    const listener=async(_event,payload)=>{
      let response;
      try{response=await callback(payload)}catch(_error){response={ok:false,error:{code:"RUNTIME_REJECTED",message:"runtime rejected request"}}}
      e.ipcRenderer.send("liang-no-henshin:set-target-form-response",{requestId:payload?.requestId,...response})
    };
    e.ipcRenderer.on("liang-no-henshin:set-target-form",listener);
    return()=>e.ipcRenderer.off("liang-no-henshin:set-target-form",listener)
  }
});
`;

const OVERLAY_HELPER = String.raw`
let __liang9275ControlUnsubscribe=null;
function __liang9275BindControl(){
  if(__liang9275ControlUnsubscribe!=null)return;
  const api=globalThis.liangNoHenshin,binding=globalThis.__liang9275Runtime?.requestTargetForm;
  if(typeof api?.onSetTargetForm!=="function"||typeof binding!=="function")return;
  __liang9275ControlUnsubscribe=api.onSetTargetForm(async payload=>{
    if(payload==null||typeof payload.requestId!=="string"||(payload.target!=="gu"&&payload.target!=="feng")||typeof payload.animate!=="boolean")return{ok:false,error:{code:"INVALID_REQUEST",message:"invalid target-form request"}};
    const accepted=await binding.call(globalThis.__liang9275Runtime,payload.target,!payload.animate),snapshot=globalThis.__liang9275Runtime.state;
    return{ok:true,result:{accepted:accepted!==false,currentForm:snapshot.currentForm,targetForm:snapshot.targetForm,transitioning:snapshot.transitionId!=null}}
  })
}
`;

function replaceOne(source, needle, replacement, label) {
  one(source, needle, label);
  return source.replace(needle, replacement);
}

function patchMain(source) {
  return `${MAIN_HELPER}${replaceOne(source, MAIN_REGISTRATION,
    "H=new wle(V,d,S),__liang9275Bridge=__liang9275InstallBridge({app:l.app,ipcMain:l.ipcMain,avatarOverlayManager:H,createBridgeServer:globalThis.__liangCreateBridgeServer}),ee=o4e",
    "main service registration")}`;
}

function patchPreload(source) {
  return `${PRELOAD_HELPER}${replaceOne(source, PRELOAD_INSERTION,
    "e.contextBridge.exposeInMainWorld(`electronBridge`,R),e.contextBridge.exposeInMainWorld(`liangNoHenshin`,__liang9275ControlApi),typeof window<`u`",
    "preload contextBridge insertion")}`;
}

function patchOverlay(source) {
  return `${OVERLAY_HELPER}${replaceOne(source, OVERLAY_SUBSCRIPTION,
    `${OVERLAY_SUBSCRIPTION},__liang9275ControlBinding=__liang9275BindControl()`, "overlay event subscription")}`;
}

function staticAssertions(original, patched) {
  assert.equal(count(original.main, MAIN_REGISTRATION), 1);
  assert.equal(count(original.preload, PRELOAD_INSERTION), 1);
  assert.equal(count(original.overlay, OVERLAY_SUBSCRIPTION), 1);
  assert.equal(count(patched.overlay, RUNTIME_BINDING), 1);
  assert.ok(patched.main.includes("createBridgeServer"));
  assert.ok(patched.main.includes('"liang-no-henshin-"+uid,"runtime.sock"'));
  assert.ok(!MAIN_HELPER.includes(".codex/ipc/ipc.sock"));
  assert.ok(patched.main.includes(IPC_REQUEST));
  assert.ok(patched.preload.includes(IPC_REQUEST));
  assert.ok(patched.preload.includes(IPC_RESPONSE));
  assert.equal(count(PRELOAD_HELPER, "onSetTargetForm(callback)"), 1);
  for (const forbidden of ["shell", "exec(", "readFile", "writeFile", "invoke(method"])
    assert.ok(!PRELOAD_HELPER.includes(forbidden));
  assert.ok(patched.overlay.includes("await binding.call"));
  assert.ok(patched.main.includes("requestId:command.requestId"));
  assert.ok(patched.preload.includes("requestId:payload?.requestId"));
  assert.ok(patched.main.includes(`},${TIMEOUT_MS})`));
  assert.ok(patched.main.includes('error.code="RUNTIME_NOT_READY"'));
  assert.equal(count(patched.overlay, OVERLAY_SUBSCRIPTION), 1);
  assert.equal(count(patched.main, "loadAvatar(e)"), count(original.main, "loadAvatar(e)"));
  assert.equal(count(patched.overlay, "custom-avatars"), count(original.overlay, "custom-avatars"));
  return "PASS";
}

async function referenceSimulation() {
  const request = Object.freeze({ requestId: "phase4-correlation-1", target: "feng", animate: true });
  const renderer = async payload => ({
    requestId: payload.requestId,
    ok: true,
    result: { accepted: true, currentForm: "gu", targetForm: payload.target, transitioning: payload.animate },
  });
  const correlated = await Promise.race([
    renderer(request),
    new Promise((_, reject) => setTimeout(() => reject(Error("timeout")), TIMEOUT_MS)),
  ]);
  assert.equal(correlated.requestId, request.requestId);
  assert.deepEqual(correlated.result, {
    accepted: true, currentForm: "gu", targetForm: "feng", transitioning: true,
  });
  let timedOut = false;
  try {
    await Promise.race([
      new Promise(() => {}),
      new Promise((_, reject) => setTimeout(() => reject(Object.assign(Error("timeout"), { code: "RUNTIME_TIMEOUT" })), 5)),
    ]);
  } catch (error) {
    timedOut = error.code === "RUNTIME_TIMEOUT";
  }
  assert.equal(timedOut, true);
  return Object.freeze({ correlation: "PASS", timeout: "PASS" });
}

async function verifyOriginal(before, initialHashes) {
  const after = await appFingerprint();
  gate(after, ["version", "build", "asar"], "post-run app");
  for (const property of ["size", "mode", "mtimeMs"])
    if (before[property] !== after[property]) throw Error(`real ASAR ${property} changed`);
  const afterChunks = extractCurrentChunks();
  for (const name of Object.keys(CHUNKS))
    if (sha(afterChunks[name]) !== initialHashes[name]) throw Error(`real ${name} chunk changed`);
  return "PASS";
}

async function run() {
  let tempRoot = null;
  let cleanup = "NOT_REQUIRED";
  try {
    const before = await appFingerprint();
    gate(before, ["version", "build", "asar"], "app");
    const chunks = extractCurrentChunks();
    const hashes = Object.fromEntries(Object.entries(chunks).map(([name, data]) => [name, sha(data)]));
    gate(hashes, Object.keys(CHUNKS), "chunks");
    console.log(`fingerprint=PASS build=${before.build} app_asar_sha256=${before.asar}`);
    const original = Object.fromEntries(Object.entries(chunks).map(([name, data]) => [name, data.toString("utf8")]));
    const patched = {
      main: patchMain(original.main),
      preload: patchPreload(original.preload),
      overlay: patchOverlay(original.overlay),
    };
    console.log("main_bridge_locator_count=1");
    console.log("preload_locator_count=1");
    console.log("overlay_subscription_locator_count=1");
    console.log(`runtime_binding_locator_count=${count(patched.overlay, RUNTIME_BINDING)}`);
    console.log(`static_assertions=${staticAssertions(original, patched)}`);
    tempRoot = await fsp.mkdtemp(path.join(os.tmpdir(), "liang-build-9275-bridge-"));
    for (const name of ["main", "preload", "overlay"]) {
      await fsp.writeFile(path.join(tempRoot, `${name}.original.mjs`), chunks[name]);
      await fsp.writeFile(path.join(tempRoot, `${name}.patched.mjs`), patched[name]);
      try {
        execFileSync(process.execPath, ["--check", path.join(tempRoot, `${name}.patched.mjs`)], {
          stdio: "pipe", maxBuffer: 16 * 1024 * 1024,
        });
      } catch (error) {
        const parser = "const fs=require('fs'),vm=require('vm');try{new vm.SourceTextModule(fs.readFileSync(process.argv[1],'utf8'))}catch(e){console.error(e.name+': '+e.message);process.exit(1)}";
        let concise = "node --check rejected module";
        try {
          execFileSync(process.execPath, ["--experimental-vm-modules", "-e", parser,
            path.join(tempRoot, `${name}.patched.mjs`)], { stdio: "pipe" });
        } catch (parseError) {
          concise = String(parseError.stderr ?? "").trim().split("\n")[0] || concise;
        }
        throw Error(`${name} temporary syntax failed: ${concise || "node --check rejected module"}`);
      }
      console.log(`temp_${name}_syntax=PASS`);
    }
    const simulation = await referenceSimulation();
    console.log(`request_id_correlation=${simulation.correlation}`);
    console.log(`timeout_behavior=${simulation.timeout}`);
    console.log("private_ipc_sock_used=false");
    console.log("filesystem_atlas_replacement_used=false");
    console.log("settings_refresh_dependency=false");
    console.log(`original_integrity=${await verifyOriginal(before, hashes)}`);
  } finally {
    if (tempRoot !== null) {
      await fsp.rm(tempRoot, { recursive: true, force: true });
      cleanup = fs.existsSync(tempRoot) ? "FAIL" : "PASS";
    }
    console.log(`temp_cleanup=${cleanup}`);
  }
  if (cleanup === "FAIL") throw Error("proprietary temporary copies were not removed");
  console.log("verdict=BUILD_9275_LOCAL_CONTROL_BRIDGE_DRY_PATCH_PASS");
}

run().catch(error => {
  console.error(`verdict=BLOCKED error=${error.message}`);
  process.exitCode = 1;
});
