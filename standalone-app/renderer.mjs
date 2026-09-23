import { ATLAS, CELL, cellPosition, frameAt, lookState } from "./animation.mjs";

const pet = document.getElementById("pet");
const overlay = document.getElementById("overlay");
let current = null;
let enteredAt = performance.now();
let lastReported = "";
let drag = null;

pet.addEventListener("pointerdown", (event) => {
  if (event.button !== 0) return;
  drag = { x: event.screenX, y: event.screenY };
  pet.setPointerCapture(event.pointerId);
  pet.classList.add("dragging");
});
pet.addEventListener("pointermove", (event) => {
  if (!drag) return;
  const dx = event.screenX - drag.x;
  const dy = event.screenY - drag.y;
  if (dx || dy) window.liangPet.moveBy(dx, dy);
  drag = { x: event.screenX, y: event.screenY };
});
function endDrag() { drag = null; pet.classList.remove("dragging"); }
pet.addEventListener("pointerup", endDrag);
pet.addEventListener("pointercancel", endDrag);

window.liangPet.onState((state) => {
  if (!current || state.playbackKey !== current.playbackKey || state.normalState !== current.normalState) {
    enteredAt = performance.now();
  }
  current = state;
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
    pet.style.visibility = "hidden";
  } else {
    overlay.style.display = "none";
    overlay.removeAttribute("src");
    pet.style.visibility = "visible";
  }
});

function tick(now) {
  if (current) {
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
