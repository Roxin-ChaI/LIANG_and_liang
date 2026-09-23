const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("liangHarness", {
  subscribe(listener) {
    ipcRenderer.on("harness-state", (_event, payload) => listener(payload));
  },
  rendered(geometry) {
    ipcRenderer.send("harness-rendered", geometry);
  },
});
