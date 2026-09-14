# Liang Wengu look mechanics

## Identity and anchor lock

- The approved source of truth is `jobs/look-cardinals/decoded/look-cardinals.png`.
- Liang Wengu remains a tired, low-energy adult man with the approved black side-parted hair, rectangular black glasses, face shape, dark navy suit, white shirt, body proportions, and muted expression.
- Feet remain planted on baseline `y=203`; the lower body stays centered at approximately `x=96` in every `192x208` cell.
- Torso, legs, shoes, arms, hands, clothing, scale, and silhouette remain fixed. No whole-body mirroring, translation, rotation, skew, squash, or stretch.

## Natural motion

- Eyes lead the gaze. Pupils move inside the existing eye apertures; eyelids and brows adjust only enough to preserve the tired expression.
- The head follows with a restrained, near-rigid yaw/pitch change. Preserve skull, hair, glasses, ears, nose, and facial proportions.
- Neck and shoulders may follow by at most a subtle pixel-scale shift when required for a believable connection, while the torso remains planted.
- Every 22.5-degree step moves the eyes and head by a similar visual amount. No adjacent snap or reversal.

## Row 9 pose family

- `000.0`: exact approved Up family; eyes and head pitch upward with no required horizontal cue.
- `022.5`: mostly Up with the first subtle screen-right eye/head cue.
- `045.0`: balanced Up-Right gaze and restrained head turn.
- `067.5`: mostly Right with a remaining upward cue.
- `090.0`: exact approved screen-Right family.
- `112.5`: mostly Right with the first subtle downward cue.
- `135.0`: balanced Down-Right gaze and restrained head pitch.
- `157.5`: mostly Down with a remaining screen-right cue; exactly one even step before approved `180` Down.

## Row 10 pose family

- `180.0`: approved Down family; eyes and head pitch downward with no required horizontal cue.
- `202.5`: mostly Down with the first subtle screen-left eye/head cue.
- `225.0`: balanced Down-Left gaze and restrained head turn.
- `247.5`: mostly Left with a remaining downward cue.
- `270.0`: approved screen-Left family.
- `292.5`: mostly Left with the first subtle upward cue.
- `315.0`: balanced Up-Left gaze and restrained head pitch.
- `337.5`: mostly Up with a remaining screen-left cue; exactly one even step before row 9 `000.0` Up.

## Prohibitions

- No new pose, gesture, prop, effect, text, UI, background, shadow, glow, or detached pixel.
- No new hairstyle, replacement eyes, altered glasses, changed suit, altered face identity, or energetic expression.
- No anti-aliasing, blur, soft transparency, or whole-sprite rotation.
