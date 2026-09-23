/** Project-owned standalone macOS desktop pet. Never loads Codex runtime. */
import { app, BrowserWindow, ipcMain, screen } from "electron";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..");
const FORM = process.env.LNH_INITIAL_FORM === "feng" ? "feng" : "gu";
let window;
let normalState = "idle";
let playbackKey = 0;
let sources;

async function dataUrl(relative) {
  const bytes = await fs.readFile(path.join(ROOT, relative));
  return `data:image/webp;base64,${bytes.toString("base64")}`;
}

function publish() {
  if (!window || window.isDestroyed()) return;
  window.webContents.send("pet-state", {
    currentForm: FORM, normalState, normalSource: sources[FORM], playbackKey,
    visualMode: "NORMAL", transitionId: null, frameIndex: null,
  });
}

function setWorkState(state) {
  if (!["idle", "running", "waiting", "review"].includes(state)) throw new TypeError("unsupported work state");
  normalState = state;
  playbackKey += 1;
  publish();
}

async function start() {
  sources = Object.freeze({
    gu: await dataUrl("assets/builds/gu/spritesheet.webp"),
    feng: await dataUrl("assets/builds/feng/spritesheet.webp"),
  });
  window = new BrowserWindow({
    width: 256, height: 256, transparent: true, frame: false, hasShadow: false,
    resizable: false, alwaysOnTop: true, skipTaskbar: true, backgroundColor: "#00000000",
    webPreferences: { preload: path.join(HERE, "preload.cjs"), contextIsolation: true,
      nodeIntegration: false, sandbox: true, webSecurity: true },
  });
  window.setAlwaysOnTop(true, "floating");
  const area = screen.getPrimaryDisplay().workArea;
  window.setPosition(area.x + area.width - 276, area.y + area.height - 276);
  ipcMain.on("pet-state-request", () => publish());
  ipcMain.on("pet-move", (_event, value) => {
    if (!Number.isFinite(value?.dx) || !Number.isFinite(value?.dy)) return;
    const [x, y] = window.getPosition();
    window.setPosition(Math.round(x + value.dx), Math.round(y + value.dy));
  });
  ipcMain.on("pet-interaction", (_event, value) => {
    if (value?.kind === "work") setWorkState(value.value);
  });
  await window.loadFile(path.join(HERE, "index.html"));
  publish();
}

app.whenReady().then(start).catch((error) => { console.error(error); app.exit(1); });
