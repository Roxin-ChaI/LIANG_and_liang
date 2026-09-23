const pet = document.getElementById("pet");
const overlay = document.getElementById("overlay");
const label = document.getElementById("label");
const decoded = new Map();
let renderSerial = 0;

function decode(url) {
  if (!decoded.has(url)) {
    const image = new Image();
    image.src = url;
    decoded.set(url, image.decode());
  }
  return decoded.get(url);
}

window.liangHarness.subscribe(async ({ visual, overlayImage }) => {
  const serial = ++renderSerial;
  await decode(visual.normalSource);
  if (overlayImage) await decode(overlayImage);
  if (serial !== renderSerial) return;
  pet.style.backgroundImage = `url("${visual.normalSource}")`;
  if (visual.visualMode === "TRANSITIONING") {
    const layout = visual.overlayLayout;
    overlay.src = overlayImage;
    overlay.style.display = "block";
    overlay.style.left = `${96 + layout.offsetLeft}px`;
    overlay.style.top = `${42 + layout.offsetTop}px`;
    overlay.style.width = `${layout.canvasWidth}px`;
    overlay.style.height = `${layout.canvasHeight}px`;
  } else {
    overlay.style.display = "none";
    overlay.removeAttribute("src");
  }
  label.textContent = `${visual.currentForm} · ${visual.transitionId ?? "idle"} · ${visual.frameIndex ?? "-"}`;
  requestAnimationFrame(() => requestAnimationFrame(() => {
    const normal = pet.getBoundingClientRect();
    const transition = overlay.getBoundingClientRect();
    window.liangHarness.rendered({
      mode: visual.visualMode,
      frameIndex: visual.frameIndex,
      transitionId: visual.transitionId,
      currentForm: visual.currentForm,
      operationToken: visual.operationToken,
      normal: { x: normal.x, y: normal.y, width: normal.width, height: normal.height },
      overlay: { x: transition.x, y: transition.y, width: transition.width, height: transition.height },
      overlayDisplay: overlay.style.display,
      overlayPointerEvents: getComputedStyle(overlay).pointerEvents,
      normalPointerEvents: getComputedStyle(pet).pointerEvents,
      overlayNaturalWidth: overlay.naturalWidth,
      overlayNaturalHeight: overlay.naturalHeight,
    });
  }));
});
