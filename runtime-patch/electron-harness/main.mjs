/** Project-owned Electron window: no Codex ASAR, auth, or production IPC. */
import { app, BrowserWindow, ipcMain, screen } from "electron";
import fs from "node:fs";
import fsp from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { createBridgeServer } from "../bridge/server.mjs";
import { createRuntimeDispatch } from "../bridge/runtime-dispatch.mjs";
import { createDualFormSourceRegistry } from "../prototype/dual-form-source.mjs";
import { loadTransitionAssets } from "../prototype/transition-assets.mjs";
import { createTransitionPlayer } from "../prototype/transition-player.mjs";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const PROJECT = path.resolve(HERE, "../..");
const TEST_BUNDLE_ID = "com.liang-no-henshin.runtime-harness";
const root = process.env.LNH_HARNESS_ROOT;
if (!root || !path.isAbsolute(root) || !path.basename(root).startsWith("liang-electron-harness-")) {
  throw new Error("LNH_HARNESS_ROOT must be an absolute project-harness temporary directory");
}
for (const name of ["HOME", "CODEX_HOME", "TMPDIR"]) {
  if (!process.env[name]?.startsWith(`${root}${path.sep}`)) {
    throw new Error(`${name} is not inside the harness temporary root`);
  }
}
const userData = path.join(root, "user-data");
const sessionData = path.join(root, "session-data");
const evidence = path.join(root, "evidence");
for (const directory of [userData, sessionData, evidence]) {
  fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
}
app.setName("Liang Runtime Harness");
app.setPath("userData", userData);
app.setPath("sessionData", sessionData);

const eventFile = path.join(evidence, "events.jsonl");
function emit(type, payload = {}) {
  const event = { type, at: new Date().toISOString(), ...payload };
  fs.appendFileSync(eventFile, `${JSON.stringify(event)}\n`, { mode: 0o600 });
  process.stdout.write(`${JSON.stringify(event)}\n`);
}

async function dataUrl(file, mime) {
  return `data:${mime};base64,${(await fsp.readFile(file)).toString("base64")}`;
}

let window;
let player;
let bridge;
let timer = null;
let overlayImages;
let registry;
let assets;
let closing = false;

function stopTimer() {
  if (timer !== null) clearInterval(timer);
  timer = null;
}

function publish(reason) {
  const visual = player.snapshot();
  const image = visual.frameSource ? overlayImages[visual.frameSource] : null;
  window.webContents.send("harness-state", { visual, overlayImage: image });
  emit("state", {
    reason,
    mode: visual.visualMode,
    currentForm: visual.currentForm,
    targetForm: visual.targetForm,
    frameIndex: visual.frameIndex,
    transitionId: visual.transitionId,
    operationToken: visual.operationToken,
    petId: visual.petId,
  });
}

function startTicking() {
  stopTimer();
  const initial = player.snapshot();
  if (initial.visualMode !== "TRANSITIONING") return;
  const operationToken = initial.operationToken;
  timer = setInterval(() => {
    if (player.snapshot().operationToken !== operationToken) {
      stopTimer();
      return;
    }
    const previous = player.snapshot();
    const next = player.advance(140);
    publish("tick");
    if (next.visualMode !== "TRANSITIONING") {
      emit("completed", {
        transitionId: previous.transitionId,
        operationToken,
        currentForm: next.currentForm,
      });
      stopTimer();
    }
  }, 140);
}

async function handleControl(line) {
  let command;
  try { command = JSON.parse(line); }
  catch { emit("control-error", { reason: "invalid-json" }); return; }
  if (command.type === "capture") {
    const name = String(command.name ?? "capture");
    if (!/^[a-z0-9_-]+$/.test(name)) throw new Error("unsafe screenshot name");
    const png = await window.webContents.capturePage();
    const file = path.join(evidence, `${name}.png`);
    await fsp.writeFile(file, png.toPNG(), { mode: 0o600 });
    emit("capture", { name, bytes: png.toPNG().length, file });
  } else if (command.type === "edge") {
    const area = screen.getPrimaryDisplay().workArea;
    const [width, height] = window.getSize();
    window.setPosition(area.x + area.width - width, area.y + area.height - height);
    emit("edge", { bounds: window.getBounds(), workArea: area });
  } else if (command.type === "interaction") {
    player.updateInteraction(command.kind, command.value);
    publish("interaction");
  } else if (command.type === "underlying") {
    player.updateUnderlyingState(command.value);
    publish("underlying");
  } else if (command.type === "stale-complete") {
    const result = player.complete(command.operationToken);
    emit("stale-complete", { completed: result.completed, stale: result.stale });
  } else if (command.type === "reset") {
    stopTimer();
    player = createTransitionPlayer({
      registry, assets, initialForm: command.initialForm === "feng" ? "feng" : "gu",
      reducedMotion: command.reducedMotion === true,
    });
    publish("reset");
  } else if (command.type === "quit") {
    closing = true;
    stopTimer();
    await bridge.stop();
    emit("quit", { socketRemoved: !fs.existsSync(bridge.socketPath) });
    app.quit();
  } else {
    emit("control-error", { reason: "unknown-command" });
  }
}

async function start() {
  const actualBundleId = process.env.LNH_HARNESS_BUNDLE_ID;
  if (actualBundleId !== TEST_BUNDLE_ID) throw new Error("test-only Bundle ID gate failed");
  const [gu, feng, loadedAssets] = await Promise.all([
    dataUrl(path.join(PROJECT, "assets/builds/gu/spritesheet.webp"), "image/webp"),
    dataUrl(path.join(PROJECT, "assets/builds/feng/spritesheet.webp"), "image/webp"),
    loadTransitionAssets({ projectRoot: PROJECT }),
  ]);
  assets = loadedAssets;
  overlayImages = {};
  for (const descriptor of Object.values(assets)) {
    for (const frame of descriptor.frames) {
      overlayImages[frame.source] = await dataUrl(path.join(PROJECT, frame.source), "image/png");
    }
  }
  registry = createDualFormSourceRegistry({
    mode: "dual-form",
    native: { petId: "custom:liang-no-henshin" },
    forms: {
      gu: { spritesheetPath: "assets/builds/gu/spritesheet.webp", spritesheetDataUrl: gu, width: 1536, height: 2288 },
      feng: { spritesheetPath: "assets/builds/feng/spritesheet.webp", spritesheetDataUrl: feng, width: 1536, height: 2288 },
    },
  });
  player = createTransitionPlayer({ registry, assets });
  window = new BrowserWindow({
    width: 420, height: 360, show: true, backgroundColor: "#18202b",
    webPreferences: {
      preload: path.join(HERE, "preload.cjs"), contextIsolation: true,
      nodeIntegration: false, sandbox: false, webSecurity: true,
    },
  });
  window.on("closed", async () => {
    if (!closing) {
      closing = true;
      stopTimer();
      await bridge?.stop();
    }
  });
  window.webContents.on("render-process-gone", (_, details) => emit("renderer-gone", { reason: details.reason }));
  window.webContents.on("did-fail-load", (_, code) => emit("renderer-load-failed", { code }));
  ipcMain.on("harness-rendered", (_, geometry) => {
    emit("renderer", geometry);
  });
  await window.loadFile(path.join(HERE, "index.html"));
  const socketPath = path.join(root, "socket", "runtime.sock");
  bridge = createBridgeServer({
    socketPath,
    dispatch: async (command) => {
      const before = player.snapshot();
      const result = await createRuntimeDispatch(player)(command);
      const after = player.snapshot();
      emit("bridge", {
        requestId: command.requestId, from: before.currentForm,
        target: command.target, animate: command.animate,
        accepted: result.accepted, operationToken: after.operationToken,
      });
      publish("bridge");
      if (after.visualMode === "TRANSITIONING" && before.operationToken !== after.operationToken) startTicking();
      else if (after.visualMode !== "TRANSITIONING") stopTimer();
      return result;
    },
  });
  const started = await bridge.start();
  emit("startup", {
    pid: process.pid, executable: process.execPath, bundleId: actualBundleId,
    userData: app.getPath("userData"), sessionData: app.getPath("sessionData"),
    socket: started.socketPath, socketMode: started.socketMode,
  });
  publish("startup");
  let pending = "";
  process.stdin.setEncoding("utf8");
  process.stdin.on("data", (chunk) => {
    pending += chunk;
    while (pending.includes("\n")) {
      const index = pending.indexOf("\n");
      const line = pending.slice(0, index);
      pending = pending.slice(index + 1);
      handleControl(line).catch((error) => emit("control-error", { reason: error.message }));
    }
  });
}

app.whenReady().then(start).catch((error) => {
  emit("fatal", { reason: error.message });
  app.quit();
});
