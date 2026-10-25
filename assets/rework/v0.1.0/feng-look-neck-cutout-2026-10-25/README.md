# Feng Look neck cutout — scoped candidate, pending user review

Source: the sixteen Look cells in the currently selected integrated Feng atlas.
The previous skin-only composition retained fragments of the donor front-facing
jaw while discarding genuine dark hair/neck shadow behind the turned ears.

This candidate:

- removes explicitly traced donor-jaw remnants;
- restores missing dark back-hair/neck-shadow pixels from the same coordinates
  in the original corresponding directional frame;
- preserves every existing skin pixel, blue clothing pixel, and all rows at
  y>=58 (including hand, sleeve, body and baseline);
- makes no changes to Gu, current runtime overrides, frozen atlases or App;
- uses no AI generation, resizing, interpolation, blur, or palette changes.

Every changed pixel is listed in `validation.json`. All sixteen enlarged neck
comparisons were inspected on a light background. 30 related tests passed,
including exact source-pixel provenance, protected anatomy, unchanged body,
binary alpha, preserved bbox, and GIF frame coverage.

Review files: `neck-light-preview.gif` and `look-light-preview.gif` show BEFORE
on the left and CANDIDATE on the right. `neck-comparison-1.png` through `4.png`
cover all directions. PNGs remain transparent; the GIF background is for review.

## Known unresolved problems — not whole-Look approval

The current integrated source already has horizontal hand seams, particularly
at 225, 247.5, 292.5, 315 and 337.5 degrees. These remain unchanged and visible
in both sides of the comparison. Light pixels on the body/shoulder edge are
also outside this neck-only patch. These issues are explicitly not PASS and
must not be hidden by crop selection or claimed fixed by this candidate.

Status: **PENDING_USER_REVIEW** for neck cleanup only. No installation or push.
