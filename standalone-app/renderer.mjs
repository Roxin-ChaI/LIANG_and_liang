import { ATLAS, CELL, cellPosition, frameAt, lookState } from "./animation.mjs";

const pet = document.getElementById("pet");
const overlay = document.getElementById("overlay");
let current = null;
let enteredAt = performance.now();
let lastReported = "";
let drag = null;
let lastLook = null;
let imageReady = false;
let renderSerial = 0;
const decoded = new Map();

function decode(url) {
  if (!decoded.has(url)) {
    const image = new Image();
    image.src = url;
    decoded.set(url, image.decode());
  }
  return decoded.get(url);
}

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
  await decode(state.normalSource);
  if (state.overlayImage) await decode(state.overlayImage);
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
  requestAnimationFrame(() => requestAnimationFrame(() => { imageReady = true; }));
});

function tick(now) {
  if (current && imageReady) {
    let row;
    let frame;
    if (current.normalState.startsWith("look:")) {
      const look = lookState(Number(current.normalState.slice(5)));
      row = look.state === "look-row-9" ? 9 : 10;
      frame = look.frame;
    } else {
      const sampled = frameAt(current.normalState, now - enteredAt);
      row = sampled.row;
      frame = sampled.frame;
    }
    const position = cellPosition(row, frame);
    pet.style.backgroundPosition = `${position.x}px ${position.y}px`;
    const reportKey = `${current.playbackKey}:${current.visualMode}:${current.frameIndex}:${row}:${frame}`;
    if (reportKey !== lastReported) {
      lastReported = reportKey;
      window.liangPet.rendered({ form: current.currentForm, state: current.normalState,
        row, frame, visualMode: current.visualMode, transitionId: current.transitionId,
        transitionFrame: current.frameIndex, overlayVisible: overlay.style.display === "block",
        windowTransparent: getComputedStyle(document.body).backgroundColor === "rgba(0, 0, 0, 0)",
        hitbox: { width: CELL.width, height: CELL.height } });
    }
  }
  requestAnimationFrame(tick);
}
requestAnimationFrame(tick);
window.liangPet.requestState();
