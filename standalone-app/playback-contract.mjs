/** Playback identity is visual, not the number of duplicate external events. */
export function shouldRestartPlayback(before, after) {
  return before.normalState !== after.normalState;
}

/** A late paint from a cancelled operation must never advance a new one. */
export function isCurrentTransitionPaint(snapshot, rendered) {
  return snapshot.visualMode === "TRANSITIONING"
    && rendered?.operationToken === snapshot.operationToken
    && rendered?.transitionFrame === snapshot.frameIndex;
}
