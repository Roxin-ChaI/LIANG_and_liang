# Gu Look neck cleanup — candidate for human review

This candidate removes the old front-facing jaw outline left around the neck
by the October 2 head/body composition. It also removes four explicitly traced
short jaw spurs. This is pixel deletion only, not generated or resampled art.

- All retained RGBA pixels are byte-identical to the integrated Gu source.
- Changes are restricted to x=73..113, y=70..78; the canonical 000 direction
  is unchanged. Blue clothing and the bright skin interior are protected.
- Hair, eyes, glasses, hands, lower collar/body, dimensions and baseline are
  unchanged. No blanket bright-edge threshold or body erosion was used.
- `validation.json` records source fingerprints and every removed coordinate.
- `look-*.png` are individual transparent frames; filename numbers are tenths
  of a degree. `gu-look-16.png` preserves the original sixteen-direction order.
- `look-light-preview.gif`: full-body BEFORE / CANDIDATE, light background.
- `neck-light-preview.gif`: enlarged neck BEFORE / CANDIDATE, light background.
- `neck-comparison-1.png` through `4.png`: all sixteen static comparisons.
- `difference-*.png`: exact per-frame deletion masks.

Self-review: all sixteen static neck comparisons inspected on a light
background; original dangling jaw arcs are removed. Human approval is pending.
Preview magnification uses nearest-neighbor only. PNGs remain RGBA; GIFs are
opaque light-background review copies, not runtime assets.

Validation: 19 tests passed across `test_gu_look_neck_cleanup.py` and
`test_approved_actions_integration.py`. Current asset overrides, original
atlases, app bundle, Feng art, and published release are unchanged.

Status: **PENDING_USER_REVIEW**. Not installed, not pushed or released.
