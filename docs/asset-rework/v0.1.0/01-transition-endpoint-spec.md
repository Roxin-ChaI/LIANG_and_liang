# Transition endpoint specification — no new animation artwork

Baseline `24b0df1`; v0.1.0 remains VISUAL_QA_FAIL. This phase does not alter standard atlases, Hooks or the incumbent App.

## Canonical pixels and coordinates

- Primary Gu endpoint: unchanged Idle row0 frame0 in the corrected-registration candidate `assets/rework/v0.1.0/gu/spritesheet.webp`. Its Idle pixels equal the formal Gu atlas; only the already-authorized five work rows differ in registration.
- Primary Feng endpoint: formal `assets/builds/feng/spritesheet.webp`, Idle row0 frame0.
- Normal cell192×208, logical horizontal anchor x=96, grounded foot y=203. The logical anchor is **not** the asymmetric sprite's alpha-hull center. Do not translate canonical Idle to make its hull center96.
- [Machine specification](endpoints/endpoint-specification.json) records exact source hashes, pixel hashes and half-open body/head/shoe reference boxes for each pose. [Reference sheet](endpoints/canonical-reference-sheet.png) labels all14 extracted references. Fixed head0–70/body70–208/shoe190–208 bands are reproducible reference regions, **not anatomical segmentation**. Head/face landmarks still require visual review.

## Idle and Running are a canonical family, not interchangeable pictures

Gu Idle and Gu Running have different head/arm/torso artwork. A single fixed endpoint cannot be pixel-identical to both. Running entry must match the **actual displayed row7 phase0–5**; exit must match the first resumed Running phase. Idle matches the approved Idle endpoint. A later artwork implementation must either supply state-matched endpoints/intermediates or an explicitly reviewed continuous canonical-handoff motion; abruptly resetting Running to Idle is forbidden. This specification alone adds neither behavior.

## Gu→Feng10 stages

- Frame0 subject pixels/registration must equal the current canonical-family source pose. No immediate alternate face, head shift, shoe relocation, scale or posture reset. Frame0 contains no effect used to conceal a mismatch.
- Early Gu stages0–2 must progressively enter the Feng posture, not replace the first stage with already-transformed Feng. Subject change leads; energy is secondary. Preserve10 ordered stages and every stage's full dwell.
- Final Feng stage must be the canonical-family target pose in its first resumed state. Idle and Running handoffs are separately approved.

## Feng→Gu8 stages

- Start must match the actual Feng source pose. Late stages5–7 gradually converge to the matching Gu Idle/Running endpoint, including head/face construction, shoes, body registration and arm pose.
- Final subject pixels equal the target canonical-family pose; no post-completion boundary-only translation or pose replacement. No trailing effect disappears solely at the normal-row takeover. Preserve8 stages and final dwell.

## Effects and QA gates

Existing oversized layouts remain: forward224×240 at(-16,-18), reverse208×224 at(-9,-14); both map to normal anchor96/baseline203. The machine spec records the corresponding allowed outer regions. Keep at least4px clear canvas margin and leave the face, glasses and torso readable; effect-bearing interiors require an authored subject/effect mask. Blue-color heuristics cannot distinguish a blue suit from energy and are not allowed as a repair mask. Effects stay hard-edge, attached/peripheral and subordinate to body change. Endpoint stages contain no effect.

Acceptance requires unchanged input hashes, stable foot/head/torso registration, pixel-exact endpoint-family matching and **independent actual-window visual continuity**. Intermediate overall bbox growth during a real transformation is not automatically a failure. No interpolation, blur, warp, copied partial face, hidden frame, frame skip or speed-up is an acceptable substitute for missing intermediate artwork.

Next gate: evaluate frozen pixels/poses without generating new characters. If safe reuse cannot satisfy both the exact boundary and neighboring-stage continuity, return **NEEDS_MANUAL_ART_REDESIGN** rather than create a misleading substitute strip.
