/** Structural render plan; does not execute or import Codex renderer code. */
const PET_WIDTH = 192;
const PET_HEIGHT = 208;
const PET_ANCHOR_X = 96;
const PET_BASELINE_Y = 203;
const PET_ID = "custom:liang-no-henshin";

function normalBox(visual) {
  return Object.freeze({
    type: "NormalPetRenderer",
    petId: PET_ID,
    width: PET_WIDTH, height: PET_HEIGHT,
    left: 0, top: 0,
    source: visual.normalSource,
    form: visual.currentForm,
    playbackEpoch: visual.playbackEpoch,
    characterVisibility: visual.visualMode === "TRANSITIONING" ? "hidden" : "visible",
    hitbox: Object.freeze({ left: 0, top: 0, width: PET_WIDTH, height: PET_HEIGHT, region: "mascot" }),
    dragCoordinates: Object.freeze({ originX: 0, originY: 0, width: PET_WIDTH, height: PET_HEIGHT }),
    clip: "overflow-hidden",
  });
}

function transitionSibling(visual) {
  if (visual.visualMode !== "TRANSITIONING") return null;
  const layout = visual.overlayLayout;
  if (!layout || !visual.frameSource || !["gu_to_feng", "feng_to_gu"].includes(visual.transitionId)
      || layout.petAnchorX !== PET_ANCHOR_X || layout.petBaselineY !== PET_BASELINE_Y) {
    throw new TypeError("invalid anchored transition visual");
  }
  const left = PET_ANCHOR_X - layout.anchorX;
  const top = PET_BASELINE_Y - layout.anchorY;
  if (left !== layout.offsetLeft || top !== layout.offsetTop) {
    throw new TypeError("frozen transition offsets differ from anchor formula");
  }
  return Object.freeze({
    type: "TransitionOverlay",
    siblingOf: "NormalPetRenderer",
    parentLevel: "outer-layout-wrapper",
    source: visual.frameSource,
    transitionId: visual.transitionId,
    frameIndex: visual.frameIndex,
    width: layout.canvasWidth, height: layout.canvasHeight,
    left, top,
    style: Object.freeze({
      position: "absolute", pointerEvents: "none", left, top,
      width: layout.canvasWidth, height: layout.canvasHeight,
    }),
    anchor: Object.freeze({ x: layout.anchorX, y: layout.anchorY }),
    clipPolicy: "outside-normal-clipped-root",
  });
}

/** Return immutable sibling tree while leaving the normal Pet box in place. */
export function renderTransitionOverlay(visual) {
  if (visual?.petId !== PET_ID || typeof visual.normalSource !== "string") {
    throw new TypeError(`visual must be for ${PET_ID} with a preloaded normal source`);
  }
  const normal = normalBox(visual);
  const overlay = transitionSibling(visual);
  return Object.freeze({
    type: "PetContainer",
    petId: PET_ID,
    width: PET_WIDTH, height: PET_HEIGHT,
    petAnchorX: PET_ANCHOR_X, petBaselineY: PET_BASELINE_Y,
    normal,
    overlay,
    layoutWrapper: Object.freeze({
      level: "outside-normal-clipped-root",
      children: Object.freeze(overlay === null ? [normal] : [normal, overlay]),
    }),
  });
}
