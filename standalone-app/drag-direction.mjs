/** Accumulate slow pointer motion; require a real reversal, not a 1 px jitter. */
export function createDragDirection(threshold = 4) {
  let pending = 0;
  let direction = null;
  return (dx) => {
    if (!Number.isFinite(dx)) return null;
    pending = Math.max(-threshold, Math.min(threshold, pending + dx));
    if (Math.abs(pending) < threshold) return null;
    const next = pending > 0 ? "running-right" : "running-left";
    if (next === direction) return null;
    direction = next;
    return next;
  };
}
