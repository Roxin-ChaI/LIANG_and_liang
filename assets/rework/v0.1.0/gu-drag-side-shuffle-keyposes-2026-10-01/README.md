# Gu rightward side-shuffle — pose preview only

The user explicitly approved the four-pose GIF motion with “动作通过” on
2026-10-01. See `motion-approval.json` for the exact approval scope.
Status: `MOTION_APPROVED_TECHNICAL_GATE_FAIL`.
This approves motion, not native pixel quality, exact Idle appearance or runtime use.
The original `qa-motion/preview.json` remains the pre-review generation record.

Four proposed poses, from left to right:

1. Screen-right heel begins lifting; screen-left foot supports.
2. Screen-right foot opens a small lateral step; feet remain separated.
3. Screen-left foot lifts and follows right without crossing the supporting leg.
4. Screen-left foot lands closer, ready for another small shuffle.

The new strip does not show the obvious crossed legs from attempt 01. This is
an assistant visual observation. The motion now has human approval;
face/upper-body consistency with canonical Idle remains unapproved.

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
