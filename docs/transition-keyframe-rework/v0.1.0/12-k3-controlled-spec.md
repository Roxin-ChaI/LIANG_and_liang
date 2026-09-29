# K3: incoming continuity before frozen Feng endpoint proximity

The current user explicitly approves K1 and final controlled K2. K2 PNG SHA256
is `565122ea1364eebd56a0d6d3b53934bef8d45d53cb1787eedf4ee1f812cdfcec`.
Old approval/QA reports remain historical and unchanged. New K3 gets its own
`assets/rework/v0.1.0/transition-keyframes/k3-controlled/` package. This commit
creates specification/masks/reference QA only, not candidate character art.

| Constraint | Approved K2 | New K3 budget |
| --- | --- | --- |
| Native canvas / registration | 192×208 / x96 | unchanged, no transform |
| Sole | y203 | unchanged |
| Head guide bbox / size | [54,4,122,84] / 68×80 | user ±5px, local method stricter: exact pixels |
| Head center | (88,44) | user ±3px, local method stricter: delta0 |
| Upper shoulder guide | width33 at y83 | exact because upper84 rows remain locked |
| Cap84:100 alpha hull | width59 | another10–14px gradual step, separately labelled proxy |
| Body70:208 bbox / width | [65,70,124,204] / 59 | each edge≤7px, width growth≤14px, center delta≤1px |

The body limits are conservative explicit local-edit allowances, not orders to
fill them. No45px body jump, face/neck shrink, global fit, rescaling or position
shift to make a centroid read x96. Registration96 remains the original canvas
anchor; K2's head center88 and body-band center94.5 are legitimate fixed source
measurements, not registration errors to correct.

The upper shoulder guide and lower cap hull are different measurements. The
cap hull includes jacket and upper arms, NOT bone-to-bone shoulder width.
Anatomical shoulder growth≤14px and plausible body/pose progression require
independent visual review. Automated tests must not relabel the wider jacket
band as an anatomical measurement or claim a completed Feng physique.

## Locked / editable regions and production method

Whole y0:84 (hair/face/glasses/ears and transparent bytes), neck/collar
x84:103,y84:101, all y140:208 (full cuffs/hands/legs/feet), and everything outside
x58:131,y84:140 are byte-locked. Only bounded upper-jacket/upper-arm pixel edits
are allowed. Use original K2 RGBA cloth donors, small integer moves, no whole
image/whole side scale, interpolation, AA, face redraw or AI generation. No
energy effect is preferred; effects may not hide the contour or fill a defect.
If a plausible further strengthening cannot be achieved inside the lock,
record MANUAL_PIXEL_ART_REQUIRED instead of relaxing identity constraints.

## Frozen B is a reference, not a target-fit instruction

B remains byte-identical at
`4ae8848d3a40e6c3d8507b7fda119d58462f3236b3202471239ee0b9c0ac506b`.
Its historical manual head guide is approximately49×54, center(88.5,31), with
about±3px uncertainty and a hand-occluded chin. Body70:208 bbox is exactly
[44,70,148,204],width104. The incoming±5px head budget cannot remove the whole
approximate19×26px K2/B head difference in one K3 step. This is an endpoint risk,
not an advance visual verdict. K3→B must be independently inspected only after
K2→K3 passes. If it visibly snaps, use B_TRANSITION_BRIDGE_REQUIRED, keep B and
the accepted incoming poses untouched, and emit no additional bridge frame here.

Technical QA includes source hashes, native RGBA, locked bytes, head size/center,
baseline, growth distribution, palette provenance, alpha0/255, zero hidden RGB,
no clipping/isolated components/new holes. Independent static review follows;
numerical PASS cannot certify artistic continuity. K3_ART_APPROVED is permitted
only when both incoming and outgoing static links pass; no human approval or
runtime eligibility is invented. No App, remaining animation, player, Scheduler,
Hooks, approved atlas, current running version or Tag is changed.

The user's controlled local-pixel mandate overrides hatch-pet's usual ImageGen
method. Its independent final visual QA gate is retained.
