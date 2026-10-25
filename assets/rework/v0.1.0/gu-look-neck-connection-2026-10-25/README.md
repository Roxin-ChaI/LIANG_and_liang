# Gu Look neck connection — revision 2, pending review

The first cleanup removed donor-jaw remnants but did not repair the cutout
slits between the directional jaw/neck and stationary collar. Its tests checked
pixel preservation, not anatomical continuity. The user rejected that result.

This revision restores the missing directional neck skin/shadow and fills
interior cutout slits using existing skin pixels from the same directional
source row. Each changed pixel has an exact source coordinate recorded in
`validation.json`. No generated art, resampling, interpolation, blur, or new
colors are used. 155 pixels are changed across 15 directions; 000 is unchanged.

Changes are limited to the small neck/collar junction. Pixels above y=74,
below y=89, and outside x=85..104 are unchanged from the previous candidate.
Hair, eyes, glasses, hands, shoulders, lower body, frame size and baseline are
preserved. The removed external dangling jaw arcs are not restored.

Review outputs:

- `neck-light-preview.gif`: previous candidate on left, revision 2 on right.
- `look-light-preview.gif`: same comparison at full-body scale.
- `neck-comparison-1.png` through `4.png`: all sixteen static comparisons.
- Individual RGBA PNGs, sixteen-frame strip and exact difference masks.

All sixteen static comparisons were inspected on a light background. The
automated checks now detect the old transparent interior slits and require
the bounded neck interior to be opaque. This is not a substitute for human
visual approval: status remains **PENDING_USER_REVIEW**.

24 relevant tests pass (neck connection, previous cleanup, integrated actions).
No App, asset override, Feng asset, frozen atlas or published release changed.
