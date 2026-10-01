# Gu rightward side-shuffle — pose preview only

The user approved the motion proposal, not this generated art.
Status: `POSE_REVIEW_PENDING_TECHNICAL_GATE_FAIL`.

Four proposed poses, from left to right:

1. Screen-right heel begins lifting; screen-left foot supports.
2. Screen-right foot opens a small lateral step; feet remain separated.
3. Screen-left foot lifts and follows right without crossing the supporting leg.
4. Screen-left foot lands closer, ready for another small shuffle.

The new strip does not show the obvious crossed legs from attempt 01. This is
an assistant visual observation, not human approval of motion or Idle identity.
All four poses and their face/upper-body consistency need human review.

## Hard constraints not yet passed

- Actual 2172×724, not native 768×208.
- Alpha has 256 values, including 453863 partially transparent pixels.
- Equal-quarter body placement is not stable: no native x=96 registration claim.
- Exact canonical Idle pixel appearance/identity is NOT verified. A similar
 -looking generated character cannot be treated as a strict match.

`source-preview.png` is the unchanged generated original, not usable runtime art.
It has not been sliced, scaled, re-centered, alpha-thresholded or composited with
Idle to hide discrepancies. No eight-frame completion or leftward derivation was
made; no Feng keypose was generated. No atlas or live App was changed.

Built-in image tool only; no CLI. References were canonical Gu Idle native and
its exact nearest-neighbor 4x enlargement. Exact prompt is in `prompt.txt`.
Source SHA256: `4325836d4f6327964a72783de919d7aa25698d411b71bf407097511b93e3deab`.

The image is retained for this requested human pose review only. It is not an
approved source and must not be automatically consumed by any build/animation.
