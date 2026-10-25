# Feng Look hand/wrist/cuff reconnection — pending review

## Cause

The old `head_mask` used all skin pixels on each scanline, including the
raised hand, and stopped at y=74. Thus the top of the hand came from the
directional frame while the bottom came from the front-facing donor. The
misaligned splice caused visible horizontal tears, especially in directions
225, 247.5, 292.5, 315 and 337.5 degrees. Neck cleanup alone could not fix this.

## Repair

Copy the coherent directional lower palm, wrist, cuff and immediate contour
from the original Feng atlas at identical coordinates. The bounded selection
includes both the old and new hand footprints to avoid leaving the obsolete
lower palm behind. It spans the old y=74 seam, rather than filling a thin line.

The binary selection uses a three-pixel margin; no image pixels are filtered,
scaled, interpolated, repainted, or generated. All copied RGBA bytes come from
the matching original direction. Head/neck pixels above y=68 are untouched;
all pixels outside x=60..97, y=68..89 are unchanged. Lower body, baseline,
canvas and direction order are preserved. Continuous cardinal hands at 000,
180 and 270 degrees remain byte-identical.

## Review

- `hand-light-preview.gif`: enlarged BEFORE / CANDIDATE on light background.
- `look-light-preview.gif`: full-body BEFORE / CANDIDATE, same direction order.
- `hand-comparison-1.png` through `4.png`: all sixteen enlarged comparisons.
- Individual transparent PNGs, sixteen-frame strip, selection and delta masks.
- `validation.json`: input fingerprints and all changed coordinates.

All sixteen final static comparisons were visually inspected, including
fingers, palm, wrist, cuff and neighboring sleeve contour. The previous
horizontal hand split is no longer visible in these comparisons. 36 relevant
tests pass, including a regression that fails on the prior hand splice and
checks exact directional hand skin across the seam.

Human visual approval is still pending. No App, asset override, Gu image,
frozen atlas, runtime logic or published release was changed. Existing light
pixels along the body/shoulder outline are a separate unresolved issue; this
candidate does not claim whole-Look approval.
