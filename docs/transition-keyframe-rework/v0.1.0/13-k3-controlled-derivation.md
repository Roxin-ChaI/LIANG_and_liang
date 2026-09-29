# One native K3 candidate from approved controlled K2

Candidate:
`assets/rework/v0.1.0/transition-keyframes/k3-controlled/candidate/K3.png`.
PNG SHA256:
`2b5651503d4d223d5c670152a1425ebafd6d55b5802f55794c6c70b3624876f6`.
Raw RGBA SHA256:
`cb5d9386568f6c67b9ed9e28448fe9a16dd4b6127bbbbc8b251897b5aba80a97`.
Only this new K3 was made; existing rejected K3 and approved A/B/K1/K2 are intact.

## Documented native pixel operation

The two upper-jacket/upper-arm panels x65:84 and x103:124 are copied from the
immutable K2 by outward1→2→3→4→5→4→3→2→1px over ordered row bands84:140.
Every small seam gap uses the original K2 panel-edge cloth pixel from that same
row. The edit plan specifies all source columns, half-open rows and offsets.
No whole-person or whole-side scaling/warp, interpolation, AA, colorsynth,
AI generation, face correction, global registration or effects. This modest
local upper-body widening is offered for review, not called a completed Feng
anatomy or a complete transformation.

1966 changed pixels, bbox[60,84,129,140]. The whole upper84 rows, neck/collar
and all y140:208 remain byte-identical. This includes full hair/face/glasses,
hands/cuffs, leg stance, feet and sole. The local offsets taper to1 before the
unchanged cuffs; the shape must also pass a visual seam/plausibility gate.

| Measurement | K2 | Candidate K3 | Delta |
| --- | --- | --- | --- |
| Head guide bbox | [54,4,122,84] | identical | 0 |
| Head size | 68×80 | 68×80 | 0×0 |
| Head center | (88,44) | (88,44) | (0,0) |
| Sole / registration | 203 / 96 | 203 / 96 | 0 / 0 |
| Body70:208 bbox | [65,70,124,204] | [60,70,129,204] | left-5,right+5 |
| Body-band width / center | 59 / 94.5 | 69 / 94.5 | +10 / 0 |
| Locked upper shoulder guide | 33 at y83 | 33 at y83 | 0 |
| Cap84:100 alpha hull | 59 | 69 | +10 |

The10px cap-hull growth is NOT measured skeletal shoulder growth. The guide at
y83 stays locked; a human-readable lower shoulder/upper-arm expansion and
plausible pose progression require independent review. Fixed registration96
does not imply body/head alpha centers must equal96.

## QA and conditional continuation

All numerical gates pass: native RGBA, sourcehash, exact locked identity, head
size/center, baseline, restrained cap/body growth, fixed body center, original
palette, alpha0/255, zero hidden RGB, one connected character, no isolated/cropped
pixels or new transparent holes. Contact/nearest3x contact/overlay/difference/
landmark guide/locked-byte report are in candidate/qa. QA guides never enter art.

Numerical PASS alone cannot open K3→B audit. A fresh independent reviewer must
inspect this exact candidate and report every required visual check PASS.
Missing, stale, incomplete or negative review remains blocked. The approved
Feng B is context, never copied over K3 to force outgoing similarity. If local
art is not credible, use K3_QA_FAIL or MANUAL_PIXEL_ART_REQUIRED and stop.
Neither this derivation nor incoming static approval implies K3_ART_APPROVED,
user art approval, completed chain approval or runtime eligibility.

The fresh independent review of the exact raw RGBA hash is now
`K2_K3_STATIC_PASS`. It confirms same identity, stable head/feet/stance, visible
restrained chest/upper-arm fullness and plausible lapel/fold/sleeve/cuff joins.
It explicitly does not infer newly drawn muscular anatomy or artistic
sufficiency toward Feng. Only the requested static K2→K3→B comparison opens
next; K3_ART_APPROVED still requires an outgoing static PASS as well.

Validation before this stage commit:29 new K3 constraint/derivation tests PASS;
full Python449 PASS,1 historical xfail,12 subtests PASS; Node216 PASS,0 failed.
Existing sources and runtime paths have no Git diff against24ddaac.

The user's local-derivation requirement overrides the normal hatch-pet
ImageGen workflow; independent visual QA remains mandatory. No App, player,
Scheduler, Hook, current running version, standard atlas or Tag was modified.
