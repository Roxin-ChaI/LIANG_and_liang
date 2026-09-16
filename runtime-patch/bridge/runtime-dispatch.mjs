/** Thin bridge adapter over the one authoritative Phase 3 transition player. */
export function createRuntimeDispatch(runtime) {
  if (!runtime || typeof runtime.requestTargetForm !== "function" || typeof runtime.snapshot !== "function") {
    throw new TypeError("runtime must expose requestTargetForm() and snapshot()");
  }
  return async function dispatch(command) {
    if (!command || typeof command.requestId !== "string"
        || (command.target !== "gu" && command.target !== "feng")
        || typeof command.animate !== "boolean") {
      const error = new Error("Invalid bridge command");
      error.code = "INVALID_REQUEST";
      throw error;
    }
    const response = runtime.requestTargetForm(command.target, {
      animate: command.animate, requestId: command.requestId,
    });
    const visual = runtime.snapshot();
    return Object.freeze({
      requestId: command.requestId,
      accepted: response.accepted === true,
      currentForm: visual.currentForm,
      targetForm: visual.targetForm,
      transitioning: visual.visualMode === "TRANSITIONING",
    });
  };
}
