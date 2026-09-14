const PET_ID = "custom:liang-no-henshin";
const FORMS = Object.freeze(["gu", "feng"]);

export class DualFormSourceError extends Error {
  constructor(code, message) {
    super(message);
    this.name = "DualFormSourceError";
    this.code = code;
  }
}

function fail(code, message) {
  throw new DualFormSourceError(code, message);
}

function isForm(form) {
  return FORMS.includes(form);
}

function normalizeSource(form, source) {
  if (
    source === null
    || typeof source !== "object"
    || typeof source.spritesheetPath !== "string"
    || typeof source.spritesheetDataUrl !== "string"
    || !source.spritesheetDataUrl.startsWith("data:image/webp;base64,")
  ) {
    fail("MISSING_FORM_SOURCE", `Resolved avatar has no valid ${form} source`);
  }
  return Object.freeze({
    spritesheetPath: source.spritesheetPath,
    spritesheetDataUrl: source.spritesheetDataUrl,
    width: source.width,
    height: source.height,
  });
}

/** Build the narrow, immutable source registry that would sit before Alo(). */
export function createDualFormSourceRegistry(resolvedAvatar) {
  if (resolvedAvatar?.mode !== "dual-form") {
    fail("DUAL_FORMS_UNAVAILABLE", "Resolved avatar is not dual-form");
  }
  if (resolvedAvatar.native?.petId !== PET_ID) {
    fail("PET_ID_MISMATCH", `Expected ${PET_ID}`);
  }
  return Object.freeze({
    petId: PET_ID,
    sources: Object.freeze({
      gu: normalizeSource("gu", resolvedAvatar.forms?.gu),
      feng: normalizeSource("feng", resolvedAvatar.forms?.feng),
    }),
  });
}

/** Select a preloaded data URL. This function performs no loading or I/O. */
export function selectFormSource(registry, form) {
  if (!isForm(form)) fail("INVALID_FORM", "form must be gu or feng");
  const source = registry?.sources?.[form];
  if (!source || typeof source.spritesheetDataUrl !== "string") {
    fail("MISSING_FORM_SOURCE", `Source registry has no ${form} source`);
  }
  return source.spritesheetDataUrl;
}

/**
 * Project one committed Phase 1 state into the existing renderer source shape.
 * currentForm and playbackEpoch remain authoritative; no second form state is kept.
 */
export function applyCommittedForm({ runtimeState, registry }) {
  if (registry?.petId !== PET_ID) fail("PET_ID_MISMATCH", `Expected ${PET_ID}`);
  const form = runtimeState?.currentForm;
  const source = selectFormSource(registry, form);
  const registryEntry = registry.sources[form];
  if (runtimeState.selectedSource !== registryEntry.spritesheetPath) {
    fail("SOURCE_STATE_MISMATCH", "Committed form and selectedSource are not atomic");
  }
  if (!Number.isInteger(runtimeState.playbackEpoch) || runtimeState.playbackEpoch < 0) {
    fail("INVALID_PLAYBACK_EPOCH", "playbackEpoch must be a non-negative integer");
  }
  return Object.freeze({
    petId: PET_ID,
    form,
    source,
    playbackEpoch: runtimeState.playbackEpoch,
    underlyingState: runtimeState.underlyingState,
  });
}
