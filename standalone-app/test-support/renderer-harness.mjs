/** Execute the actual app-owned renderer with injectable decode/RAF/clock.
 * This is a deterministic unit harness, not Desktop or actual-window evidence.
 */
import fs from "node:fs";
import vm from "node:vm";
import * as animation from "../animation.mjs";
import { createPaintAckGate } from "../paint-ack.mjs";
import { createDragDirection } from "../drag-direction.mjs";

export function rendererHarness({ source, libraries = {} } = {}) {
  const code = source ?? fs.readFileSync(new URL("../renderer.mjs", import.meta.url), "utf8");
  let now = 0;
  let raf = [];
  const errors = [], reports = [], decoded = [], waiting = new Map();
  const callbacks = {};
  const pointerCallbacks = {};
  const interactions = [], moves = [];
  const element = () => ({ style: {}, classList: { add() {}, remove() {} },
    addEventListener(name, fn) { pointerCallbacks[name] = fn; }, setPointerCapture() {}, removeAttribute() {},
    getBoundingClientRect: () => ({ left: 32, top: 24, width: 192, height: 208 }) });
  const elements = { pet: element(), overlay: element() };
  const context = vm.createContext({ ...animation, createPaintAckGate, createDragDirection, ...libraries,
    document: { getElementById: id => elements[id], visibilityState: "visible", body: {} },
    window: { addEventListener() {}, liangPet: {
      onState(fn) { callbacks.state = fn; }, onPreloadImages(fn) { callbacks.preload = fn; },
      rendered(value) { reports.push(value); }, preloadDone() {}, requestState() {},
      interaction(kind, value) { interactions.push({kind, value}); },
      moveBy(x, y) { moves.push({x, y}); },
    } },
    Image: class {
      decode() { decoded.push(this.src); return waiting.get(this.src)?.promise ?? Promise.resolve(); }
    },
    getComputedStyle: () => ({ backgroundColor: "rgba(0, 0, 0, 0)" }),
    performance: { now: () => now }, requestAnimationFrame(fn) { raf.push(fn); return raf.length; },
    console: { error(...items) { errors.push({ name: "console", message: items.join(" ") }); } },
  });
  vm.runInContext(code.replace(/^import[^\n]+\n/gm, ""), context, { filename: "actual-renderer.mjs" });
  return {
    reports, errors, decoded, interactions, moves,
    pointer(name, event = {}) { pointerCallbacks[name]({button: 0, pointerId: 1, ...event}); },
    setNow(value) { now = value; },
    receive(value) { return callbacks.state(value); },
    holdDecode(url) {
      let resolve, reject;
      const promise = new Promise((a, b) => { resolve = a; reject = b; });
      waiting.set(url, { promise, resolve, reject });
      return { resolve, reject };
    },
    paint(timestamp, performanceTime = timestamp) {
      now = performanceTime;
      const pending = raf;
      raf = [];
      for (const callback of pending) {
        try { callback(timestamp); }
        catch (error) { errors.push({ name: error.name, message: error.message }); }
      }
    },
    get pendingCallbacks() { return raf.length; },
  };
}

export function transitionState(overrides = {}) {
  return { currentForm: "gu", normalSource: "gu-atlas", normalState: "review", underlyingState: "review",
    playbackKey: "1:1", visualMode: "TRANSITIONING", transitionId: "gu_to_feng",
    frameIndex: 4, operationToken: "operation-1", overlayImage: "frame-4",
    overlayLayout: { offsetLeft: -16, offsetTop: -18, canvasWidth: 224, canvasHeight: 240 }, ...overrides };
}
