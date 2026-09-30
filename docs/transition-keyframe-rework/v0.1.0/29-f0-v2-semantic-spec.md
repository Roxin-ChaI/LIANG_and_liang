# F0-v2: morphology completion followed by a separate Feng entrance

The earlier F0 is retired as a final candidate; its files and failed QA remain historical evidence. KF2 is the sole base for F0-v2. K1/K2/K3/KB1/KB2/KF1/KF2, formal atlases and B remain immutable.

Morph completes the broad Feng shoulders/torso, basic blue suit and Feng head-size range in the existing low-arm stance. It intentionally retains KF2's relaxed expression. Entry subsequently performs the sharp expression, hand-to-chin pose, fist adjustment, wider stance and remaining garment details. Entry may not hide another large body or skull transformation.

## Morph contract

- Native 192×208 RGBA; registration x=96; sole baseline y=203.
- Head target guide `[63,4,113,59]` = 50×55, center (88,31.5), versus KF2 52×59, center (88,33.5). These are silhouette guides including some collar/neck, not exact anatomical segmentation.
- Source facial crop `[67,28,110,56]` is copied byte-for-byte to `[67,26,110,54]`: brows, eyes, glasses, nose and mouth retain expression, with a documented 2px upward placement. No redrawing or interpolated head scaling.
- Both hand/cuff regions `[60,130,79,155]` and `[112,130,135,155]`, plus all feet pixels at y≥192, remain identical in place, including alpha and transparent RGB.
- Broad body-band guide 96–104px and single-step width change ≤10px; trouser outer edges may move at most 3px per side while preserving the inner gap, stance and sole positions. Body-band width includes arms and cannot alone certify Feng anatomy.
- Mandatory visual review separately checks completed Feng form, face, arms, pants and jacket. Geometry and unchanged expression are not sufficient to approve an unfinished body.

## Entry contract

Only a static `F0_MORPH_ENDPOINT_APPROVED` permits F0-v2→B audit. Direct connection must retain head/body identity. If the expression, raised arm, wide stance and clothing detail changes cannot connect directly, record `FENG_ENTRY_ANIMATION_REQUIRED` and plan 2–4 separate entry poses. Do not generate those poses or constrain them to the old 10-frame Morph budget.

Manual construction uses KF2 pixels, local integer part placement, flat native palette selection and documented seam edits. No whole-person generation/scaling, antialiasing, extra KF bridges, runtime integration or tag. Human final artwork approval remains separately recorded.
