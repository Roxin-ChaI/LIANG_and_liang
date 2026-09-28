/** A paint acknowledgment belongs to the committed renderer generation, not
 * merely to the frame that was queued. Dropped stale work must remain retryable.
 */
export function createPaintAckGate({ schedule, send, currentSerial }) {
  const pending = new Set();
  let delivered = null;
  return ({ serial, key, payload }) => {
    const identity = JSON.stringify([serial, key]);
    if (identity === delivered || pending.has(identity)) return false;
    pending.add(identity);
    schedule(() => schedule(() => {
      pending.delete(identity);
      if (serial !== currentSerial()) return;
      send(payload);
      delivered = identity;
    }));
    return true;
  };
}
