/** Codex Pet v2 cell map, reproduced without importing any Codex runtime. */
export const CELL = Object.freeze({ width: 192, height: 208, columns: 8, rows: 11 });
export const ATLAS = Object.freeze({ width: 1536, height: 2288 });

export const STATES = Object.freeze({
  idle: Object.freeze({ row: 0, frames: 6, durations: [280, 110, 110, 140, 140, 320], repeat: Infinity }),
  "running-right": Object.freeze({ row: 1, frames: 8, duration: 120, lastDuration: 220, repeat: Infinity }),
  "running-left": Object.freeze({ row: 2, frames: 8, duration: 120, lastDuration: 220, repeat: Infinity }),
  waving: Object.freeze({ row: 3, frames: 4, duration: 140, lastDuration: 280, repeat: 3 }),
  jumping: Object.freeze({ row: 4, frames: 5, duration: 140, lastDuration: 280, repeat: Infinity }),
  failed: Object.freeze({ row: 5, frames: 8, duration: 140, lastDuration: 240, repeat: 3 }),
  waiting: Object.freeze({ row: 6, frames: 6, duration: 150, lastDuration: 260, repeat: 3 }),
  running: Object.freeze({ row: 7, frames: 6, duration: 120, lastDuration: 220, repeat: 3 }),
  review: Object.freeze({ row: 8, frames: 6, duration: 150, lastDuration: 280, repeat: 3 }),
  "look-row-9": Object.freeze({ row: 9, frames: 8, duration: 150, lastDuration: 150, repeat: Infinity }),
  "look-row-10": Object.freeze({ row: 10, frames: 8, duration: 150, lastDuration: 150, repeat: Infinity }),
});

export function lookState(direction) {
  if (!Number.isInteger(direction) || direction < 0 || direction > 15) throw new RangeError("look direction must be 0..15");
  return { state: direction < 8 ? "look-row-9" : "look-row-10", frame: direction % 8 };
}

function durations(descriptor, slowIdle) {
  const base = descriptor.durations ?? Array.from({ length: descriptor.frames }, (_, index) =>
    index === descriptor.frames - 1 ? descriptor.lastDuration : descriptor.duration);
  return slowIdle ? base.map((value) => value * 6) : base;
}

export function frameAt(state, elapsedMs, { slowIdle = false } = {}) {
  const descriptor = STATES[state];
  if (!descriptor) throw new TypeError(`unknown animation state: ${state}`);
  if (!Number.isFinite(elapsedMs) || elapsedMs < 0) throw new RangeError("elapsedMs must be non-negative and finite");
  const lengths = durations(descriptor, slowIdle);
  const pass = lengths.reduce((sum, value) => sum + value, 0);
  if (descriptor.repeat !== Infinity && elapsedMs >= pass * descriptor.repeat) {
    return Object.freeze({ ...frameAt("idle", elapsedMs - pass * descriptor.repeat, { slowIdle: true }), completed: true });
  }
  let position = elapsedMs % pass;
  for (let index = 0; index < lengths.length; index += 1) {
    if (position < lengths[index]) {
      return Object.freeze({ state, row: descriptor.row, frame: index, completed: false, slowIdle });
    }
    position -= lengths[index];
  }
  throw new Error("unreachable animation position");
}

export function cellPosition(row, frame) {
  if (!Number.isInteger(row) || row < 0 || row >= CELL.rows
      || !Number.isInteger(frame) || frame < 0 || frame >= CELL.columns) {
    throw new RangeError("atlas cell out of bounds");
  }
  return Object.freeze({ x: -(frame * CELL.width), y: -(row * CELL.height) });
}
