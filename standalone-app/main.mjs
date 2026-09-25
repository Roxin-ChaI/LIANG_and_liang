/** Project-owned standalone macOS desktop pet. Never loads Codex runtime. */
import { app, BrowserWindow, ipcMain, Menu, powerMonitor, screen } from "electron";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { createDualFormSourceRegistry } from "../runtime-patch/prototype/dual-form-source.mjs";
import { loadTransitionAssets } from "../runtime-patch/prototype/transition-assets.mjs";
import { createTransitionPlayer } from "../runtime-patch/prototype/transition-player.mjs";
import { createPetEventAdapter } from "./events.mjs";
import { createFormScheduler, expectedFormAt } from "./schedule.mjs";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..");
const TEST = process.env.LNH_STANDALONE_TEST === "1";
const TEST_ROOT = TEST ? process.env.LNH_STANDALONE_TEST_ROOT : null;
if (TEST && (!TEST_ROOT || !path.isAbsolute(TEST_ROOT))) throw new Error("test mode needs an absolute temporary root");
app.setName("Liang no Henshin");
if (TEST) app.setPath("userData", path.join(TEST_ROOT, "user-data"));

let window;
let player;
let adapter;
let scheduler;
let transitionTimer = null;
let stateEpoch = 0;
let requestSerial = 0;
let overlayImages;
let clockOverride = TEST && process.env.LNH_TEST_INITIAL_TIME ? new Date(process.env.LNH_TEST_INITIAL_TIME) : null;

function clock() { return clockOverride ?? new Date(); }
function emit(type, payload = {}) {
  if (TEST) process.stdout.write(`${JSON.stringify({ type, ...payload })}\n`);
}
async function dataUrl(relative, mime) {
  const bytes = await fs.readFile(path.join(ROOT, relative));
  return `data:${mime};base64,${bytes.toString("base64")}`;
}
function stopTransitionTick() {
  if (transitionTimer !== null) clearInterval(transitionTimer);
  transitionTimer = null;
}
function publish(reason) {
  if (!window || window.isDestroyed()) return;
  const visual = player.snapshot();
  const image = visual.frameSource ? overlayImages[visual.frameSource] : null;
  window.webContents.send("pet-state", {
    ...visual, overlayImage: image, playbackKey: `${visual.playbackEpoch}:${stateEpoch}`,
  });
  emit("state", { reason, form: visual.currentForm, target: visual.targetForm,
    normalState: visual.normalState, visualMode: visual.visualMode,
    transitionId: visual.transitionId, frameIndex: visual.frameIndex,
    operationToken: visual.operationToken });
}
function startTransitionTick() {
  stopTransitionTick();
  if (player.snapshot().visualMode !== "TRANSITIONING") return;
  const token = player.snapshot().operationToken;
  transitionTimer = setInterval(() => {
    if (player.snapshot().operationToken !== token) { stopTransitionTick(); return; }
    const before = player.snapshot();
    const after = player.advance(140);
    publish("transition-tick");
    if (after.visualMode !== "TRANSITIONING") {
      stopTransitionTick();
      emit("transition-complete", { transitionId: before.transitionId, form: after.currentForm,
        normalState: after.normalState, underlyingState: after.underlyingState, operationToken: token });
    }
  }, 140);
}
function dispatch(event, reason = "event") {
  const before = player.snapshot();
  const result = adapter.dispatch(event);
  const after = player.snapshot();
  if (event.type === "work-state" || after.normalState !== before.normalState) stateEpoch += 1;
  publish(reason);
  if (after.visualMode === "TRANSITIONING" && before.operationToken !== after.operationToken) startTransitionTick();
  else if (after.visualMode !== "TRANSITIONING") stopTransitionTick();
  return result;
}

async function testControl(command) {
  if (command.type === "work") dispatch({ type: "work-state", state: command.state }, "test-work");
  else if (command.type === "form") dispatch({ type: "target-form", form: command.form,
    animate: command.animate !== false, requestId: `test-${++requestSerial}` }, "test-form");
  else if (command.type === "interaction") dispatch({ type: "interaction", kind: command.kind, value: command.value }, "test-interaction");
  else if (command.type === "clock") {
    const date = new Date(command.value);
    if (Number.isNaN(date.valueOf())) throw new TypeError("invalid test clock");
    clockOverride = date;
    const result = await scheduler.reconcile("test-clock");
    emit("schedule", { now: date.toISOString(), expectedForm: result?.expectedForm,
      nextTransition: result?.nextTransition.toISOString() });
  } else if (command.type === "capture") {
    if (!/^[a-z0-9_-]+$/.test(command.name)) throw new TypeError("invalid capture name");
    const file = path.join(TEST_ROOT, `${command.name}.png`);
    const image = await window.webContents.capturePage();
    await fs.writeFile(file, image.toPNG());
    emit("capture", { name: command.name, file });
  } else if (command.type === "inspect") {
    const dom = await window.webContents.executeJavaScript(`(() => {
      const pet = document.getElementById('pet');
      const box = pet.getBoundingClientRect();
      return { background: getComputedStyle(pet).backgroundImage.slice(0, 60),
        opacity: getComputedStyle(pet).opacity, size: [box.width, box.height],
        visibility: document.visibilityState, ready: document.readyState };
    })()`);
    emit("inspect", { dom, visible: window.isVisible(), focused: window.isFocused() });
  } else if (command.type === "move") {
    window.setPosition(Math.round(command.x), Math.round(command.y));
    emit("window-position", { bounds: window.getBounds() });
  } else if (command.type === "simulate-drag") {
    const before = window.getBounds();
    window.webContents.sendInputEvent({ type: "mouseMove", x: 96, y: 100 });
    window.webContents.sendInputEvent({ type: "mouseDown", x: 96, y: 100, button: "left", clickCount: 1 });
    await new Promise((resolve) => setTimeout(resolve, 60));
    window.webContents.sendInputEvent({ type: "mouseMove", x: 126, y: 100, button: "left" });
    await new Promise((resolve) => setTimeout(resolve, 100));
    window.webContents.sendInputEvent({ type: "mouseUp", x: 126, y: 100, button: "left", clickCount: 1 });
    emit("synthetic-drag", { before, after: window.getBounds() });
  } else if (command.type === "quit") {
    scheduler.stop();
    stopTransitionTick();
    emit("quit");
    app.quit();
  } else throw new TypeError("unsupported test command");
}

async function start() {
  const [gu, feng, assets] = await Promise.all([
    dataUrl("assets/builds/gu/spritesheet.webp", "image/webp"),
    dataUrl("assets/builds/feng/spritesheet.webp", "image/webp"),
    loadTransitionAssets({ projectRoot: ROOT }),
  ]);
  const registry = createDualFormSourceRegistry({ mode: "dual-form", native: { petId: "custom:liang-no-henshin" },
    forms: {
      gu: { spritesheetPath: "assets/builds/gu/spritesheet.webp", spritesheetDataUrl: gu, width: 1536, height: 2288 },
      feng: { spritesheetPath: "assets/builds/feng/spritesheet.webp", spritesheetDataUrl: feng, width: 1536, height: 2288 },
    } });
  overlayImages = {};
  for (const descriptor of Object.values(assets)) {
    for (const frame of descriptor.frames) overlayImages[frame.source] = await dataUrl(frame.source, "image/png");
  }
  player = createTransitionPlayer({ registry, assets, initialForm: expectedFormAt(clock()) });
  adapter = createPetEventAdapter(player);
  window = new BrowserWindow({
    width: 256, height: 256, transparent: true, frame: false, hasShadow: false,
    resizable: false, alwaysOnTop: true, skipTaskbar: true, backgroundColor: "#00000000",
    webPreferences: { preload: path.join(HERE, "preload.cjs"), contextIsolation: true,
      nodeIntegration: false, sandbox: true, webSecurity: true },
  });
  window.setAlwaysOnTop(true, "floating");
  const area = screen.getPrimaryDisplay().workArea;
  window.setPosition(area.x + area.width - 276, area.y + area.height - 276);
  ipcMain.on("pet-state-request", () => publish("renderer-ready"));
  ipcMain.on("pet-move", (_event, value) => {
    if (!Number.isFinite(value?.dx) || !Number.isFinite(value?.dy)) return;
    const [x, y] = window.getPosition();
    window.setPosition(Math.round(x + value.dx), Math.round(y + value.dy));
    emit("window-position", { bounds: window.getBounds() });
  });
  ipcMain.on("pet-interaction", (_event, value) => {
    try { dispatch({ type: "interaction", kind: value.kind, value: value.value }, "pointer"); }
    catch (error) { emit("interaction-error", { reason: error.message }); }
  });
  ipcMain.on("pet-context-menu", () => {
    const menu = Menu.buildFromTemplate([
      { label: "Work state", submenu: [
        { label: "Idle", click: () => dispatch({ type: "work-state", state: "idle" }, "menu") },
        { label: "Running", click: () => dispatch({ type: "work-state", state: "running" }, "menu") },
        { label: "Waiting", click: () => dispatch({ type: "work-state", state: "waiting" }, "menu") },
        { label: "Review", click: () => dispatch({ type: "work-state", state: "review" }, "menu") },
      ] },
      { label: "Form", submenu: [
        { label: "Gu", click: () => dispatch({ type: "target-form", form: "gu", requestId: `menu-${++requestSerial}` }, "menu") },
        { label: "Feng", click: () => dispatch({ type: "target-form", form: "feng", requestId: `menu-${++requestSerial}` }, "menu") },
      ] },
      { type: "separator" },
      { label: "Quit Liang no Henshin", click: () => app.quit() },
    ]);
    menu.popup({ window });
  });
  ipcMain.on("pet-rendered", (_event, value) => emit("renderer", value));
  window.webContents.on("render-process-gone", (_event, details) => emit("renderer-gone", { reason: details.reason }));
  window.webContents.on("did-fail-load", (_event, code) => emit("renderer-load-failed", { code }));
  await window.loadFile(path.join(HERE, "index.html"));
  emit("startup", { pid: process.pid, bounds: window.getBounds(), transparent: true,
    frame: false, initialForm: player.snapshot().currentForm, userData: app.getPath("userData") });
  publish("startup");
  scheduler = createFormScheduler({ now: clock, onTarget: async (form, metadata) => {
    dispatch({ type: "target-form", form, animate: metadata.reason !== "startup",
      requestId: `schedule-${++requestSerial}` }, `schedule-${metadata.reason}`);
  } });
  await scheduler.reconcile("startup");
  powerMonitor.on("resume", () => { void scheduler.reconcile("resume"); });
  if (TEST) {
    let pending = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (chunk) => {
      pending += chunk;
      while (pending.includes("\n")) {
        const index = pending.indexOf("\n");
        const line = pending.slice(0, index);
        pending = pending.slice(index + 1);
        try { void testControl(JSON.parse(line)).catch((error) => emit("test-error", { reason: error.message })); }
        catch (error) { emit("test-error", { reason: error.message }); }
      }
    });
  }
}

app.whenReady().then(start).catch((error) => { console.error(error); emit("fatal", { reason: error.message }); app.exit(1); });
app.on("window-all-closed", () => { scheduler?.stop(); stopTransitionTick(); app.quit(); });
