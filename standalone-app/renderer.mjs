import { ATLAS, CELL, cellPosition, frameAt, lookState } from "./animation.mjs";
import { createPaintAckGate } from "./paint-ack.mjs";

const pet = document.getElementById("pet");
const overlay = document.getElementById("overlay");
let current = null;
let enteredAt = performance.now();
let drag = null;
let lastLook = null;
let imageReady = false;
let renderSerial = 0;
const decoded = new Map();
const reportPaint = createPaintAckGate({
  schedule: requestAnimationFrame,
  send: payload => window.liangPet.rendered(payload),
  currentSerial: () => renderSerial,
});

function decode(url) {
  if (!decoded.has(url)) {
    const image = new Image();
    image.src = url;
    const promise = image.decode().catch(error => {
      decoded.delete(url);
      throw error;
    });
    decoded.set(url, promise);
  }
  return decoded.get(url);
}

window.liangPet.onPreloadImages(async (images) => {
  try {
    await Promise.all(images.map(decode));
    window.liangPet.preloadDone({ count: images.length, success: true });
  } catch {
    window.liangPet.preloadDone({ count: images.length, success: false });
  }
});

pet.addEventListener("pointerenter", () => window.liangPet.interaction("hover", true));
pet.addEventListener("pointerleave", () => window.liangPet.interaction("hover", false));
pet.addEventListener("contextmenu", (event) => { event.preventDefault(); window.liangPet.showMenu(); });
window.addEventListener("pointermove", (event) => {
  if (drag) return;
  const bounds = pet.getBoundingClientRect();
  const dx = event.clientX - (bounds.left + bounds.width / 2);
  const dy = event.clientY - (bounds.top + bounds.height / 2);
  const direction = Math.round((Math.atan2(dx, -dy) * 180 / Math.PI + 360) % 360 / 22.5) % 16;
  if (direction !== lastLook) {
    lastLook = direction;
    window.liangPet.interaction("look", direction);
  }
});
window.addEventListener("pointerleave", () => {
  lastLook = null;
  window.liangPet.interaction("look", null);
  window.liangPet.interaction("hover", false);
});

pet.addEventListener("pointerdown", (event) => {
  if (event.button !== 0) return;
  const space = event.screenX || event.screenY ? "screen" : "client";
  drag = { space, x: space === "screen" ? event.screenX : event.clientX,
    y: space === "screen" ? event.screenY : event.clientY };
  pet.setPointerCapture(event.pointerId);
  pet.classList.add("dragging");
});
pet.addEventListener("pointermove", (event) => {
  if (!drag) return;
  const x = drag.space === "screen" ? event.screenX : event.clientX;
  const y = drag.space === "screen" ? event.screenY : event.clientY;
  const dx = x - drag.x;
  const dy = y - drag.y;
  if (dx || dy) {
    window.liangPet.moveBy(dx, dy);
    if (Math.abs(dx) >= 4) window.liangPet.interaction("drag", dx > 0 ? "running-right" : "running-left");
  }
  drag = { ...drag, x, y };
});
function endDrag() {
  drag = null;
  pet.classList.remove("dragging");
  window.liangPet.interaction("drag", null);
}
pet.addEventListener("pointerup", endDrag);
pet.addEventListener("pointercancel", endDrag);

window.liangPet.onState(async (state) => {
  const serial = ++renderSerial;
  imageReady = false;
  try {
    await decode(state.normalSource);
    if (state.overlayImage) await decode(state.overlayImage);
  } catch {
    // Do not acknowledge an image that has never decoded or skip its frame.
    console.error("pet frame decode failed");
    return;
  }
  if (serial !== renderSerial) return;
  if (!current || state.playbackKey !== current.playbackKey || state.normalState !== current.normalState) {
    enteredAt = performance.now();
  }
  current = state;
  imageReady = false;
  pet.style.backgroundImage = `url("${state.normalSource}")`;
  pet.style.backgroundSize = `${ATLAS.width}px ${ATLAS.height}px`;
  if (state.visualMode === "TRANSITIONING" && state.overlayImage) {
    const layout = state.overlayLayout;
    overlay.src = state.overlayImage;
    overlay.style.display = "block";
    overlay.style.left = `${32 + layout.offsetLeft}px`;
    overlay.style.top = `${24 + layout.offsetTop}px`;
    overlay.style.width = `${layout.canvasWidth}px`;
    overlay.style.height = `${layout.canvasHeight}px`;
    pet.style.opacity = "0";
  } else {
    overlay.style.display = "none";
    overlay.removeAttribute("src");
    pet.style.opacity = "1";
  }
  requestAnimationFrame(() => requestAnimationFrame(() => {
    if (serial === renderSerial) imageReady = true;
  }));
});

function tick(now) {
  try {
    if (current && imageReady) {
      let row;
      let frame;
      if (current.normalState.startsWith("look:")) {
        const look = lookState(Number(current.normalState.slice(5)));
        row = look.state === "look-row-9" ? 9 : 10;
        frame = look.frame;
      } else {
        // RAF timestamps describe the beginning of a callback batch; a state
        // epoch sampled asynchronously with performance.now() can be newer.
        // A not-yet-started normal animation is frame 0, never negative age.
        const sampled = frameAt(current.normalState, Math.max(0, now - enteredAt), {
          // Desktop's notification row is finite, but an active standalone task owns
          // Running until Stop/timeout; do not visually fall back to Idle mid-task.
          held: current.normalState === "running" && current.underlyingState === "running",
        });
        row = sampled.row;
        frame = sampled.frame;
      }
      const position = cellPosition(row, frame);
      pet.style.backgroundPosition = `${position.x}px ${position.y}px`;
      const reportKey = `${current.playbackKey}:${current.operationToken}:${current.visualMode}:${current.frameIndex}:${row}:${frame}`;
      const serial = renderSerial;
      const payload = { form: current.currentForm, state: current.normalState,
        row, frame, visualMode: current.visualMode, transitionId: current.transitionId,
        transitionFrame: current.frameIndex, operationToken: current.operationToken,
        overlayVisible: overlay.style.display === "block",
        visibility: document.visibilityState,
        windowTransparent: getComputedStyle(document.body).backgroundColor === "rgba(0, 0, 0, 0)",
        hitbox: { width: CELL.width, height: CELL.height } };
      // Deduplicate successful delivery, not the act of queueing a callback.
      reportPaint({ serial, key: reportKey, payload });
    }
  } finally {
    // An unexpected sampling error remains visible but cannot permanently
    // destroy the sole RAF chain and leave main waiting for frame4 forever.
    requestAnimationFrame(tick);
  }
}
requestAnimationFrame(tick);
window.liangPet.requestState();
