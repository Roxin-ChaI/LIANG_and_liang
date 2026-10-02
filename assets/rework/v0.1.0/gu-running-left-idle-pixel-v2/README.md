# Gu leftward shuffle — native candidate for GIF review

2026-10-02: user selected the displayed shuffle choreography (“采用图中的预览动作”).
The earlier four-pose preview remains the motion guide; the current native
rightward v2 keeps this lift/reach/plant/follow sequence. This leftward version
uses the same sequence with the leading and following screen-side legs swapped
and horizontal travel reversed. The selection approves the motion direction,
not every pixel of newly derived eight-frame art.

## Construction

Every output pixel comes from canonical Gu Idle. Rows 0–160 preserve hair,
face, glasses, torso, arms and hands byte-for-byte at their original position.
Integer lower-leg row movements reverse the travel without mirroring the whole
character. This preserves the asymmetric hairstyle, face and jacket exactly.
No interpolation, character scaling, palette replacement or ImageGen was used.

Eight native 192×208 RGBA frames form `running-left.png` (1536×208).
Each has one connected foreground, binary alpha, transparent RGB zero, unchanged
upper-body registration x=96 and a supporting foot on baseline y=203.
`qa/validation.json` includes all source row mappings and overlaps. A few rows
overlap as a shin bends; knees, cuffs and planted-foot movement need visual
review even though mechanical checks pass.

## Review media

- `qa/running-left-preview.gif`: 8 frames, 120/130 ms alternating, 1 s loop.
- `qa/running-left-slow.gif`: 8 frames, 250 ms each, 2 s loop.
- `qa/left-right-preview.gif`: left candidate beside unchanged right v2,
  synchronized frame order and timing.
- `qa/contact-sheet.png`: all eight native poses enlarged 2× nearest-neighbor.

No preview alignment is applied. GIF gray backgrounds and palette conversion
are review-only; native PNGs remain transparent. Status is
`TECHNICAL_PASS_VISUAL_REVIEW_PENDING`. Neither this candidate nor the paired
preview is an App integration or live drag test.
