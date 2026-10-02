# Gu rightward shuffle: visibly stepped v2 candidate

Status: `TECHNICAL_PASS_VISUAL_REVIEW_PENDING`.

The user rejected both the subtle native v1 and the generated intermediate
attempts. The earlier four-pose source remains the motion reference. This v2
reconstructs the same four action phases with four between phases using the
formal Gu Idle sprite's pixels. It does **not** claim to be the original four
PNG frames copied verbatim; their partial alpha and changed facial pixels
prevented native runtime acceptance. The source image is unchanged.

The cycle moves the screen-right foot outward by up to 12 native pixels, plants
it, then raises and brings the screen-left foot after it. Foot offset changes
are checked before the next frame is built. The stance sequence is:

1. Screen-left supports; screen-right lifts.
2. Screen-left supports; screen-right reaches right.
3. Screen-left supports; screen-right descends.
4. Both grounded; screen-right has planted.
5. Screen-right supports; screen-left lifts.
6. Screen-right supports; screen-left follows.
7. Both grounded, feet closer together.
8. Screen-left supports; screen-right begins lifting into frame 1.

All frames use 192×208 RGBA. Head, face, hair, glasses, jacket, torso and arms
in rows 0–160 are byte-identical to canonical Gu Idle in every frame. Below
that, original Idle lower-leg pixels are moved by integer row offsets.
No frame is rescaled or color-interpolated. Alpha is exactly 0/255, all colors
come from Idle, and a grounded foot reaches y=203 in every frame. The logical
body registration remains x=96. These mechanical checks do not certify that
the knee and cuff silhouettes look natural.

`qa/running-right-preview.gif` has 8 frames at alternating 120/130 ms, a 1 s
loop. `qa/running-right-slow.gif` uses 250 ms per frame. GIFs display at 2×
nearest-neighbor; the dark gray background and GIF palette are preview-only.
`qa/contact-sheet.png` shows all eight frames and `qa/legs-contact-sheet.png`
enlarges the edited region. `qa/validation.json` records per-frame support,
registration, palette and previous-frame offset checks.

The choreography and anatomy still need human review. In particular, frames
3–5 and 7–1 should be checked for planted-foot sliding, rightward readability
and trouser-cuff continuity. No mirror, leftward version, atlas replacement or
App integration was made.
