# Single K2: controlled K1-origin pixel derivation

The new final candidate is
`assets/rework/v0.1.0/transition-keyframes/k2-controlled/candidate-locked-hands/K2.png`.
PNG SHA256: `565122ea1364eebd56a0d6d3b53934bef8d45d53cb1787eedf4ee1f812cdfcec`.
Raw RGBA SHA256: `3462ff0391745732801c58d2538f50c78a66b0bc39d66beabef8efc7d5b30e98`.
K1 is the user-approved immutable source, not the obsolete whole-image AI K2.

## Actual modifications

Two local jacket/upper-arm panels, columns69:84 and103:121, are translated
outward by integer1→2→3→4→3→2→1px across documented row bands84:140.
This is not a scale/warp of either half or the whole character. Small resulting
cloth gaps are filled from the original K1 panel-edge RGBA pixel in the same
row. The plan names every panel, row band and donor rule. All copied pixels
come from immutable K1; no color interpolation, novel palette, AI, energy
overlay, head correction, global scaling or registration translation.

1904 pixels differ, confined to [65,84,124,140]. Whole head/top84 rows and the
neck/collar are exact. Whole y140:208, including cuffs, hands, leg stance and
feet, are exact. New K2 does not strengthen the head or legs to fit existing K3.

| Measurement | K1 | Final K2 | Delta |
| --- | --- | --- | --- |
| Head guide bbox | [54,4,122,84] | identical | 0 |
| Head size | 68×80 | 68×80 | 0×0 |
| Head center | (88,44) | (88,44) | (0,0) |
| Baseline / registration | 203 / 96 | 203 / 96 | 0 / 0 |
| Body70:208 bbox | [69,70,121,204] | [65,70,124,204] | left-4,right+3 |
| Body-band width / center | 52 / 95 | 59 / 94.5 | +7 / -0.5 |
| Upper shoulder guide at y83 | 33 | 33 (locked) | 0 |
| Shoulder-cap84:100 alpha hull | 51 | 59 | +8 |

The cap hull is explicitly **not anatomical shoulder width**. A fixed upper
guide is retained, with modest widening of the lower shoulder caps/upper arms.
The instruction offsets are bilateral4px at their maximum, but the measured
whole body-hull right edge expands only3px: its old maximum occurs at a
different row. Tests use actual measured extrema, not assumed target bounds.

## Rejected draft and tightened hand gate

The first draft used a taper ending at y146. Its initial broad numerical gate
passed, but source-pixel inspection found altered skin at y142:146. This
violated the chosen hands-unmodified derivation policy, though the user's
general K2 request would allow tiny hand motion. It was rejected before any
static approval; its image/initial report and explicit rejected disposition
remain in `k2-controlled/candidate/` as diagnostic evidence, NOT the final K2.
The original draft row plan is retained in its disposition. No failed artwork
was silently replaced or labelled PASS. Final edits stop at y140, and an extra
byte comparison locks all y140:208. A regression changes an upper-hand pixel
inside the old broad edit rectangle and confirms chain QA remains blocked.

## Gates and evidence

All final numerical/byte gates pass: identity, geometry, baseline, restrained
body/cap growth, original palette, binary alpha, zero hidden RGB, one connected
character, no isolated/clipped pixels or new transparent holes. Byte comparison
and native contact/nearest3x QA/difference/overlay/landmark guide are in the final
candidate's `qa/`. Guide colors exist only in QA, not in the transparent art.

Numerical PASS does not certify face identity or cloth plausibility. An
independent static reviewer must inspect this final candidate's actual pixels
and its raw RGBA hash. Stale/draft/missing/incomplete review cannot open K3 chain
QA. Human K2 art approval remains PENDING and runtime eligibility remains false.
No App, animation, player, Scheduler, Hook, approved K1 or atlas modifications.

The final fresh independent review is `K1_K2_STATIC_PASS`: same Gu identity,
stable head/neck, modest lower-cap/fullness change, plausible lapel/sleeve/cuff
seams and no visible pixel artifacts. It explicitly calls the change a subtle
fuller-jacket/upper-arm step, not proven anatomical widening or a more confident
pose. Whether the artistic strengthening is sufficient remains a user decision.
`K2_ART_APPROVED` is not falsely recorded as human approval. Static PASS opens
only the requested read-only K1→K2→existing K3 comparison.

The local-pixel mandate overrides hatch-pet's normal ImageGen method. Its
independent visual check remains mandatory. This stage is not actual App QA.
