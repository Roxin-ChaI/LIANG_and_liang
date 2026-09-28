/** Animated reverse requests settle the visible sequence, then apply latest target.
 * No transition frame is dropped and task/interaction state stays owned by player.
 */
export function createFormRequestQueue() {
  let pending = null;
  return Object.freeze({
    consider(event, snapshot) {
      if (event?.type !== "target-form") return { deferred: false };
      if (!["gu", "feng"].includes(event.form)) throw new TypeError("invalid form");
      if (event.animate !== undefined && typeof event.animate !== "boolean") throw new TypeError("invalid animate");
      if (snapshot.visualMode !== "TRANSITIONING" || event.animate === false) {
        pending = null;
        return { deferred: false };
      }
      if (event.form === snapshot.targetForm) {
        // Latest intent reverted to the current operation: withdraw reversal.
        pending = null;
        return { deferred: false };
      }
      pending = Object.freeze({ ...event });
      return { deferred: true, target: event.form, requestId: event.requestId };
    },
    take() { const value = pending; pending = null; return value; },
    peek() { return pending; },
  });
}
