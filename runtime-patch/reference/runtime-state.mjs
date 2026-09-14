const FORM_VALUES = Object.freeze(["gu", "feng"]);
const VISUAL_NORMAL = "NORMAL";
const VISUAL_TRANSITIONING = "TRANSITIONING";

const TRANSITION_ENDPOINTS = Object.freeze({
  gu_to_feng: Object.freeze({ from: "gu", to: "feng" }),
  feng_to_gu: Object.freeze({ from: "feng", to: "gu" }),
});

const DEFAULT_CONFIG = Object.freeze({
  schemaVersion: 1,
  initialForm: "gu",
  forms: Object.freeze({
    gu: Object.freeze({ spritesheetPath: "forms/gu/spritesheet.webp" }),
    feng: Object.freeze({ spritesheetPath: "forms/feng/spritesheet.webp" }),
  }),
  transitions: Object.freeze({
    gu_to_feng: Object.freeze({
      from: "gu",
      to: "feng",
      frames: Object.freeze(["transform/gu_to_feng/gu_to_feng_01.png"]),
      frameDurationMs: 140,
    }),
    feng_to_gu: Object.freeze({
      from: "feng",
      to: "gu",
      frames: Object.freeze(["transform/feng_to_gu/feng_to_gu_01.png"]),
      frameDurationMs: 140,
    }),
  }),
});

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function hasExactKeys(value, requiredKeys) {
  if (!isObject(value)) return false;
  const actual = Object.keys(value).sort();
  const expected = [...requiredKeys].sort();
  return actual.length === expected.length && actual.every((key, index) => key === expected[index]);
}

function isForm(value) {
  return FORM_VALUES.includes(value);
}

/** Return true only for a normalized, Pet-root-relative, forward-slash path. */
export function isSafePetRelativePath(value) {
  if (typeof value !== "string" || value.length === 0 || value.includes("\0")) return false;
  if (value.startsWith("/") || /^[A-Za-z]:/.test(value) || value.includes("\\")) return false;
  const segments = value.split("/");
  return segments.every((segment) => segment.length > 0 && segment !== "." && segment !== "..");
}

/** Validate the sidecar's semantic rules without relying on a JSON Schema package. */
export function validateRuntimeConfig(config) {
  const errors = [];
  if (!hasExactKeys(config, ["schemaVersion", "initialForm", "forms", "transitions"])) {
    errors.push("sidecar must contain exactly schemaVersion, initialForm, forms, and transitions");
  }
  if (!isObject(config) || config.schemaVersion !== 1) errors.push("schemaVersion must equal 1");
  if (!isObject(config) || !isForm(config.initialForm)) errors.push("initialForm must be gu or feng");

  if (!isObject(config?.forms) || !hasExactKeys(config.forms, FORM_VALUES)) {
    errors.push("forms must contain exactly gu and feng");
  } else {
    for (const form of FORM_VALUES) {
      const source = config.forms[form];
      if (!hasExactKeys(source, ["spritesheetPath"])) {
        errors.push(`forms.${form} must contain exactly spritesheetPath`);
      } else if (!isSafePetRelativePath(source.spritesheetPath)) {
        errors.push(`forms.${form}.spritesheetPath must be Pet-root-relative`);
      }
    }
  }

  const transitionNames = Object.keys(TRANSITION_ENDPOINTS);
  if (!isObject(config?.transitions) || !hasExactKeys(config.transitions, transitionNames)) {
    errors.push("transitions must contain exactly gu_to_feng and feng_to_gu");
  } else {
    for (const name of transitionNames) {
      const transition = config.transitions[name];
      const expected = TRANSITION_ENDPOINTS[name];
      if (!hasExactKeys(transition, ["from", "to", "frames", "frameDurationMs"])) {
        errors.push(`${name} must contain exactly from, to, frames, and frameDurationMs`);
        continue;
      }
      if (transition.from !== expected.from || transition.to !== expected.to) {
        errors.push(`${name} endpoints must be ${expected.from} to ${expected.to}`);
      }
      if (!Array.isArray(transition.frames) || transition.frames.length === 0) {
        errors.push(`${name}.frames must be non-empty`);
      } else if (transition.frames.some((frame) => !isSafePetRelativePath(frame))) {
        errors.push(`${name}.frames must contain only Pet-root-relative paths`);
      }
      if (!Number.isInteger(transition.frameDurationMs) || transition.frameDurationMs <= 0) {
        errors.push(`${name}.frameDurationMs must be a positive integer`);
      }
    }
  }

  return Object.freeze({ valid: errors.length === 0, errors: Object.freeze(errors) });
}

function cloneConfig(config) {
  return Object.freeze({
    schemaVersion: config.schemaVersion,
    initialForm: config.initialForm,
    forms: Object.freeze(Object.fromEntries(FORM_VALUES.map((form) => [
      form,
      Object.freeze({ spritesheetPath: config.forms[form].spritesheetPath }),
    ]))),
    transitions: Object.freeze(Object.fromEntries(Object.keys(TRANSITION_ENDPOINTS).map((name) => {
      const transition = config.transitions[name];
      return [name, Object.freeze({
        from: transition.from,
        to: transition.to,
        frames: Object.freeze([...transition.frames]),
        frameDurationMs: transition.frameDurationMs,
      })];
    }))),
  });
}

function normalizeAvailability(availability = {}) {
  return Object.freeze({
    atlases: Object.freeze({
      gu: availability.atlases?.gu !== false,
      feng: availability.atlases?.feng !== false,
    }),
    transitions: Object.freeze({
      gu_to_feng: availability.transitions?.gu_to_feng !== false,
      feng_to_gu: availability.transitions?.feng_to_gu !== false,
    }),
  });
}

/** Create an immutable reference state. Runtime asset readiness is injected. */
export function createRuntimeState({
  initialForm,
  runtimeConfig = DEFAULT_CONFIG,
  reducedMotion = false,
  underlyingState = "idle",
  availability,
} = {}) {
  const validation = validateRuntimeConfig(runtimeConfig);
  if (!validation.valid) throw new TypeError(validation.errors.join("; "));
  const form = initialForm ?? runtimeConfig.initialForm;
  if (!isForm(form)) throw new TypeError("initialForm must be gu or feng");
  if (typeof reducedMotion !== "boolean") throw new TypeError("reducedMotion must be boolean");
  if (typeof underlyingState !== "string" || underlyingState.length === 0) {
    throw new TypeError("underlyingState must be a non-empty string");
  }

  const config = cloneConfig(runtimeConfig);
  const readiness = normalizeAvailability(availability);
  if (!readiness.atlases[form]) throw new TypeError("initial form atlas must be available");

  return Object.freeze({
    currentForm: form,
    targetForm: form,
    visualState: VISUAL_NORMAL,
    transition: null,
    operationToken: null,
    underlyingState,
    reducedMotion,
    selectedSource: config.forms[form].spritesheetPath,
    playbackEpoch: 0,
    nextOperationSequence: 1,
    lastCancelReason: null,
    config,
    availability: readiness,
  });
}

function withResponse(state, requestId, fields = {}) {
  return Object.freeze({
    state,
    response: Object.freeze({
      accepted: true,
      currentForm: state.currentForm,
      targetForm: state.targetForm,
      transitioning: state.visualState === VISUAL_TRANSITIONING,
      requestId,
      ...fields,
    }),
  });
}

function reject(state, requestId, reason) {
  return withResponse(state, requestId, { accepted: false, reason });
}

function issueToken(state) {
  return Object.freeze({
    operationToken: `form-operation-${state.nextOperationSequence}`,
    nextOperationSequence: state.nextOperationSequence + 1,
  });
}

function transitionName(from, to) {
  return `${from}_to_${to}`;
}

function commitForm(state, targetForm, operationToken = state.operationToken) {
  return Object.freeze({
    ...state,
    currentForm: targetForm,
    targetForm,
    visualState: VISUAL_NORMAL,
    transition: null,
    operationToken,
    selectedSource: state.config.forms[targetForm].spritesheetPath,
    playbackEpoch: state.playbackEpoch + 1,
    lastCancelReason: null,
  });
}

/**
 * Apply the logical bridge command without side effects.
 * Returns { state, response }; callers own storage and rendering transactions.
 */
export function setTargetForm(state, command) {
  const requestId = command?.requestId;
  if (!isObject(command)) return reject(state, requestId, "invalid-command");
  if (!isForm(command.target)) return reject(state, requestId, "invalid-form");
  if (typeof command.animate !== "boolean") return reject(state, requestId, "invalid-animate");
  if (typeof requestId !== "string" || requestId.length === 0) {
    return reject(state, requestId, "invalid-request-id");
  }

  if (state.visualState === VISUAL_TRANSITIONING && command.target === state.targetForm) {
    return withResponse(state, requestId, {
      noOp: true,
      operationToken: state.operationToken,
      reason: "duplicate-active-target",
    });
  }

  if (state.visualState === VISUAL_TRANSITIONING && command.target !== state.targetForm) {
    const issued = issueToken(state);
    const cancelled = Object.freeze({
      ...state,
      targetForm: state.currentForm,
      visualState: VISUAL_NORMAL,
      transition: null,
      operationToken: issued.operationToken,
      nextOperationSequence: issued.nextOperationSequence,
      lastCancelReason: "superseded",
    });
    if (command.target === cancelled.currentForm) {
      return withResponse(cancelled, requestId, {
        noOp: true,
        cancelled: true,
        operationToken: issued.operationToken,
        reason: "returned-to-committed-form",
      });
    }
    return setTargetForm(cancelled, command);
  }

  if (command.target === state.currentForm) {
    return withResponse(state, requestId, { noOp: true, reason: "already-current" });
  }
  if (!state.availability.atlases[command.target]) {
    return reject(state, requestId, "target-atlas-unavailable");
  }

  const name = transitionName(state.currentForm, command.target);
  const transitionAvailable = state.availability.transitions[name];
  if (!command.animate || state.reducedMotion || !transitionAvailable) {
    const committed = commitForm(state, command.target);
    return withResponse(committed, requestId, {
      transitionFallback: command.animate && !state.reducedMotion && !transitionAvailable,
      reducedMotion: state.reducedMotion,
    });
  }

  const issued = issueToken(state);
  const descriptor = state.config.transitions[name];
  const nextState = Object.freeze({
    ...state,
    targetForm: command.target,
    visualState: VISUAL_TRANSITIONING,
    transition: Object.freeze({
      name,
      from: descriptor.from,
      to: descriptor.to,
      frames: descriptor.frames,
      frameDurationMs: descriptor.frameDurationMs,
      requestId,
    }),
    operationToken: issued.operationToken,
    nextOperationSequence: issued.nextOperationSequence,
    lastCancelReason: null,
  });
  return withResponse(nextState, requestId, { operationToken: issued.operationToken });
}

/** Commit a transition only when its completion token is still active. */
export function completeTransition(state, operationToken) {
  const requestId = state.transition?.requestId;
  if (state.visualState !== VISUAL_TRANSITIONING || operationToken !== state.operationToken) {
    return withResponse(state, requestId, {
      accepted: false,
      completed: false,
      stale: true,
      reason: "stale-operation-token",
    });
  }
  const committed = commitForm(state, state.targetForm, operationToken);
  return withResponse(committed, requestId, { completed: true, operationToken });
}

/** Cancel active playback and invalidate its completion token. */
export function cancelTransition(state, reason = "cancelled") {
  const requestId = state.transition?.requestId;
  if (state.visualState !== VISUAL_TRANSITIONING) {
    return withResponse(state, requestId, { noOp: true, reason: "not-transitioning" });
  }
  const issued = issueToken(state);
  const cancelled = Object.freeze({
    ...state,
    targetForm: state.currentForm,
    visualState: VISUAL_NORMAL,
    transition: null,
    operationToken: issued.operationToken,
    nextOperationSequence: issued.nextOperationSequence,
    lastCancelReason: reason,
  });
  return withResponse(cancelled, requestId, {
    cancelled: true,
    operationToken: issued.operationToken,
    reason,
  });
}

/** Update native task state without disturbing the higher-priority transition. */
export function setUnderlyingState(state, underlyingState) {
  if (typeof underlyingState !== "string" || underlyingState.length === 0) {
    throw new TypeError("underlyingState must be a non-empty string");
  }
  return Object.freeze({ ...state, underlyingState });
}

/** Preserve ordinary native-pet behavior when the sidecar is absent or invalid. */
export function resolvePetRuntime(nativePet, sidecar, options = {}) {
  if (sidecar === undefined || sidecar === null) {
    return Object.freeze({ mode: "native", pet: nativePet });
  }
  const validation = validateRuntimeConfig(sidecar);
  if (!validation.valid) {
    return Object.freeze({ mode: "native", pet: nativePet, sidecarErrors: validation.errors });
  }
  return Object.freeze({
    mode: "dual-form",
    pet: nativePet,
    runtimeState: createRuntimeState({ ...options, runtimeConfig: sidecar }),
  });
}
