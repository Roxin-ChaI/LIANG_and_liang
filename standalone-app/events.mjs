/** Narrow app-owned event contract; future Codex adapters must target this. */
export function createPetEventAdapter(player) {
  if (!player?.requestTargetForm || !player?.updateUnderlyingState || !player?.updateInteraction) {
    throw new TypeError("transition player is required");
  }
  return Object.freeze({
    dispatch(event) {
      if (!event || typeof event !== "object") throw new TypeError("event is required");
      if (event.type === "work-state") {
        if (!["idle", "running", "waiting", "review", "failed", "waving"].includes(event.state)) {
          throw new TypeError("unsupported work state");
        }
        return player.updateUnderlyingState(event.state);
      }
      if (event.type === "target-form") {
        if (!["gu", "feng"].includes(event.form)) throw new TypeError("invalid form");
        return player.requestTargetForm(event.form, {
          animate: event.animate !== false, requestId: event.requestId ?? `standalone-${event.form}`,
        });
      }
      if (event.type === "interaction") return player.updateInteraction(event.kind, event.value);
      throw new TypeError("unsupported pet event");
    },
  });
}
