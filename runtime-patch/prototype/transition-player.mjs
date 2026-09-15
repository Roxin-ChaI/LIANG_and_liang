/** Deterministic, I/O-free form transition player for the project-side PoC. */
import {
  completeTransition, createRuntimeState, setTargetForm, setUnderlyingState,
} from "../reference/runtime-state.mjs";
import { applyCommittedForm } from "./dual-form-source.mjs";
import { TRANSITION_SPECS } from "./transition-assets.mjs";

const PET_ID = "custom:liang-no-henshin";
const NORMAL = "NORMAL";
const TRANSITIONING = "TRANSITIONING";

function validAssets(assets, name) {
  const spec = TRANSITION_SPECS[name];
  const item = assets?.[name];
  return !!item && item.from === spec.from && item.to === spec.to
    && item.frameDurationMs === 140 && Array.isArray(item.frames) && item.frames.length === spec.count
    && item.layout?.canvasWidth === spec.width && item.layout?.canvasHeight === spec.height
    && item.layout?.petAnchorX === 96 && item.layout?.petBaselineY === 203
    && item.layout?.offsetLeft === 96 - item.layout?.anchorX
    && item.layout?.offsetTop === 203 - item.layout?.anchorY
    && item.frames.every((frame, index) => frame?.source
      === `assets/transform-overlay/${name}/${name}_${String(index + 1).padStart(2, "0")}.png`
      && frame.width === spec.width && frame.height === spec.height);
}

function runtimeConfig(registry) {
  const transitions = Object.fromEntries(Object.entries(TRANSITION_SPECS).map(([name, spec]) => [name, {
    from: spec.from, to: spec.to,
    frames: Array.from({ length: spec.count }, (_, index) =>
      `assets/transform-overlay/${name}/${name}_${String(index + 1).padStart(2, "0")}.png`),
    frameDurationMs: 140,
  }]));
  return {
    schemaVersion: 1, initialForm: "gu",
    forms: {
      gu: { spritesheetPath: registry.sources.gu.spritesheetPath },
      feng: { spritesheetPath: registry.sources.feng.spritesheetPath },
    },
    transitions,
  };
}

/** Priority: transition > drag > hover > task > idle/look. */
function nativeVisual(interaction, underlyingState) {
  if (interaction.drag) return interaction.drag;
  if (interaction.hover) return "jumping";
  if (underlyingState !== "idle") return underlyingState;
  return interaction.look === null ? "idle" : `look:${interaction.look}`;
}

export function createTransitionPlayer({
  registry, assets, initialForm = "gu", underlyingState = "idle",
  reducedMotion = false, availability = {},
} = {}) {
  if (registry?.petId !== PET_ID || !registry?.sources?.gu || !registry?.sources?.feng) {
    throw new TypeError(`registry must contain both preloaded atlases for ${PET_ID}`);
  }
  const assetReady = Object.fromEntries(Object.keys(TRANSITION_SPECS).map((name) => [
    name, validAssets(assets, name) && availability.transitions?.[name] !== false,
  ]));
  let state = createRuntimeState({
    initialForm, underlyingState, reducedMotion,
    runtimeConfig: runtimeConfig(registry),
    availability: {
      atlases: availability.atlases,
      transitions: assetReady,
    },
  });
  let elapsedMs = 0;
  let transitionFallback = false;
  let interaction = Object.freeze({ drag: null, hover: false, look: null });

  function snapshot() {
    const transitioning = state.visualState === TRANSITIONING;
    const descriptor = transitioning ? assets[state.transition.name] : null;
    const frameIndex = transitioning ? Math.floor(elapsedMs / descriptor.frameDurationMs) : null;
    const normal = applyCommittedForm({ runtimeState: state, registry });
    return Object.freeze({
      visualMode: state.visualState,
      currentForm: state.currentForm,
      targetForm: state.targetForm,
      transitionId: transitioning ? state.transition.name : null,
      frameIndex,
      frameSource: transitioning ? descriptor.frames[frameIndex].source : null,
      overlayLayout: transitioning ? descriptor.layout : null,
      underlyingState: state.underlyingState,
      normalState: nativeVisual(interaction, state.underlyingState),
      normalSource: normal.source,
      petId: normal.petId,
      operationToken: state.operationToken,
      playbackEpoch: state.playbackEpoch,
      transitionFallback,
    });
  }

  function requestTargetForm(target, { animate = true, requestId = `request-${target}` } = {}) {
    const before = state;
    const result = setTargetForm(state, { target, animate, requestId });
    state = result.state;
    if (state.visualState !== TRANSITIONING || state.operationToken !== before.operationToken) {
      elapsedMs = 0;
    }
    transitionFallback = result.response.transitionFallback === true;
    return Object.freeze({ ...result.response, visual: snapshot() });
  }

  function complete(operationToken) {
    if (state.visualState !== TRANSITIONING || operationToken !== state.operationToken) {
      return Object.freeze({ completed: false, stale: true, visual: snapshot() });
    }
    const descriptor = assets[state.transition.name];
    if (elapsedMs < descriptor.frames.length * descriptor.frameDurationMs) {
      return Object.freeze({ completed: false, stale: false, reason: "last-frame-incomplete", visual: snapshot() });
    }
    const result = completeTransition(state, operationToken);
    state = result.state;
    elapsedMs = 0;
    transitionFallback = false;
    return Object.freeze({ completed: result.response.completed === true, stale: false, visual: snapshot() });
  }

  function advance(ms) {
    if (!Number.isFinite(ms) || ms < 0) throw new RangeError("advance(ms) requires finite non-negative milliseconds");
    if (state.visualState !== TRANSITIONING) return snapshot();
    const descriptor = assets[state.transition.name];
    const total = descriptor.frames.length * descriptor.frameDurationMs;
    elapsedMs = Math.min(total, elapsedMs + ms);
    if (elapsedMs === total) complete(state.operationToken);
    return snapshot();
  }

  function updateUnderlyingState(nextState) {
    state = setUnderlyingState(state, nextState);
    return snapshot();
  }

  function updateInteraction(kind, value) {
    if (kind === "drag" && value !== null && value !== "running-left" && value !== "running-right") {
      throw new TypeError("drag must be running-left, running-right, or null");
    }
    if (kind === "hover" && typeof value !== "boolean") throw new TypeError("hover must be boolean");
    if (kind === "look" && value !== null && (!Number.isInteger(value) || value < 0 || value > 15)) {
      throw new TypeError("look must be a direction index 0..15 or null");
    }
    if (!["drag", "hover", "look"].includes(kind)) throw new TypeError("unknown interaction");
    interaction = Object.freeze({ ...interaction, [kind]: value });
    return snapshot();
  }

  return Object.freeze({
    snapshot, advance, complete, updateUnderlyingState, updateInteraction,
    requestTargetForm, startTransition: requestTargetForm,
  });
}
