const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("liangPet", Object.freeze({
  onState(listener) {
    if (typeof listener !== "function") throw new TypeError("listener must be a function");
    const handler = (_event, state) => listener(state);
    ipcRenderer.on("pet-state", handler);
    return () => ipcRenderer.removeListener("pet-state", handler);
  },
  requestState() { ipcRenderer.send("pet-state-request"); },
  moveBy(dx, dy) { ipcRenderer.send("pet-move", { dx, dy }); },
  interaction(kind, value) { ipcRenderer.send("pet-interaction", { kind, value }); },
  showMenu() { ipcRenderer.send("pet-context-menu"); },
  rendered(payload) { ipcRenderer.send("pet-rendered", payload); },
}));
