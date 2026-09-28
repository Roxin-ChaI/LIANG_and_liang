# Reverse source extraction repair

Scope: extraction only. No redraw, App integration, endpoint replacement,
player change or standard atlas change. This is NOT reverse animation approval.

## Actual source evidence

Source: `assets/rework/v0.1.0/transition-full/sources/feng-to-gu-generated-retry.png`
(1704×923 RGBA). Eight substantial alpha>16 connected components reveal two
four-pose rows. Their first-row soles reach y=482; second-row poses begin at
y=486. The valid region boundary is y=484, not the equal-grid y=461/462.
The source contains the shoes; fixed grid slicing, not missing source art,
caused the prior crop. Bounds also determine column gaps independently per row.

All original RGBA pixels, including faint fringe and hidden RGB, are assigned
exactly once to native inspection regions. Rebuilding the source from those
regions is byte-exact. Native PNGs use one 464×511 inspection canvas and do not
resize or redraw. Its y=490 baseline is explicitly NOT the runtime baseline.

## Authorized normalization

Native pose heights are 421–475 px; they cannot fit the existing 208×224 overlay
with no scaling. The user explicitly authorized **one common nearest-neighbor
normalization for all eight frames**. The retained native report records the
earlier no-scaling conflict; this authorization resolves that conflict only.

The common scale is 200/475 (0.42105263157894735), one nearest-neighbor resize
of each original region, with no per-frame fit or color interpolation. Binary
alpha threshold128 removes source translucent fringe; retained RGB values are
unchanged and transparent RGB is zero. Counts are recorded, not concealed.
Integer registration follows: lower-body hull center within 95.5–96.5, sole
y=203 on 192×208 normal canvas. This hull is a registration proxy, not a claim
about anatomical centers. Source pose-dependent height/width changes remain.

Runtime copies are 208×224 with local anchor(105,217), placement offset(-9,-14),
therefore logical pet anchor(96,203). Their normal-area crop is pixel-identical
to each 192×208 normalized frame. No foreground is lost during canvas placement.

## Art gate

Result: `EXTRACTION_PASS_ART_UNAPPROVED`. All eight complete poses are retained,
but the source still needs identity, endpoint and pose-continuity approval.
Do not attach these frames to the player or claim the full reverse animation
passes. No generated or normalized pixels replace A/B/C/D.

Independent visual review: extraction PASS, source art complete. It confirms
all eight hair/hands/shoes are uncropped. Separately, 03→04 loses about20 px of
height in the original art, and07 is a newly drawn Gu approximation rather than
canonical D. Those are unresolved art issues, not extraction defects.
Targeted extraction/endpoint regression:22 tests PASS.

Evidence root:
`assets/rework/v0.1.0/transition-keyframes/feng-to-gu-extraction/`

- `native-inspection-frames/`: exact source RGBA, no resampling.
- `qa/validation.json`: actual source regions and native reconstruction proof.
- `shared-normalized/normal-frames/`: eight 192×208 hard-edge candidates.
- `shared-normalized/runtime-frames/`: eight existing-overlay-sized copies.
- `shared-normalized/qa/contact-sheet.png`: complete shoes/hands/hair overview.
- `shared-normalized/qa/validation.json`: common scale and per-frame accounting.

Reproduce with bundled workspace Python:
`python -m tools.extract_transition_pose_regions --output <new-path> --normalize-shared-nearest`
(requires the explicit scale authorization; existing outputs are never overwritten).
