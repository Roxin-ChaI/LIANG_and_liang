# Phase 3B — endpoint geometry and feasibility

`STRUCTURAL_ENDPOINT_CHECK = BLOCKED` and `VISUAL_REVIEW_REQUIRED = true`.
No Phase 3B runtime frames were regenerated, no original 1254×1254 transition
PNG was changed, and neither formal Gu/Feng atlas was changed. Commit 2 is
intentionally not attempted because the Commit 1 analysis gives no
direction-wide scale meeting both endpoint heights.

## Measurement method

`tools/analyze_transition_endpoints.py` reads the 1536×2288 formal v2
Gu/Feng atlases at row 0, frame 0 (192×208), the four Phase 3A runtime
endpoints, and their approved 1254×1254 originals. It reports full nonzero
alpha bboxes separately from a deterministic character-body extremal proxy:
alpha ≥128 plus near-neutral dark pixels (hair, suit, shoes), excluding cyan
energy. The comparison sheets draw the full alpha bbox in red and the dark
body proxy in amber. This mask is appropriate for endpoint scale analysis:
the extremal dark pixels at each endpoint are visible hair and shoe pixels,
while detached blue particles do not determine body height. Body geometry
remains marked `LIKELY` until the user visually reviews the comparison sheets.

All bboxes are `(left, top, right-exclusive, bottom-exclusive)` in the final
192×208 cell. `baseline` is the visible body proxy's last row, which can
differ from the Phase 3A *full-alpha* baseline.

| Image | Body/proxy bbox | Width | Height | Center x | Baseline | Top y |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Gu formal idle | (54, 4, 122, 204) | 68 | 200 | 88.0 | 203 | 4 |
| Gu→Feng 01 | (65, 45, 120, 204) | 55 | 159 | 92.5 | 203 | 45 |
| Gu→Feng 10 | (46, 21, 141, 203) | 95 | 182 | 93.5 | 202 | 21 |
| Feng formal idle | (44, 4, 148, 204) | 104 | 200 | 96.0 | 203 | 4 |
| Feng→Gu 01 | (51, 21, 146, 203) | 95 | 182 | 98.5 | 202 | 21 |
| Feng→Gu 08 | (39, 40, 94, 204) | 55 | 164 | 66.5 | 203 | 40 |

For completeness, the full-alpha runtime bboxes are G→F 01
`(64,45,129,204)`, G→F 10 `(25,21,167,204)`, F→G 01
`(24,21,168,204)`, and F→G 08 `(38,35,155,204)`. Every full-alpha
bbox ends at y=203, but the body proxy at the Feng endpoints ends at y=202.
The Gu formal idle full-alpha center is x=88, not x=96; centering by x=96
would itself create an entry/exit shift relative to the approved atlas.

## Endpoint deltas against formal idle

| Junction | Body height delta | Body width delta | Center delta | Body baseline delta |
| --- | ---: | ---: | ---: | ---: |
| Gu idle → G→F 01 | −41 px | −13 px | +4.5 px | 0 px |
| G→F 10 → Feng idle | −18 px | −9 px | −2.5 px | −1 px |
| Feng idle → F→G 01 | −18 px | −9 px | +2.5 px | −1 px |
| F→G 08 → Gu idle | −36 px | −13 px | −21.5 px | 0 px |

The height mismatch is far outside the proposed ≤2 px tolerance. Integer
translation could fix baseline/center where canvas clearance allows, but
cannot change height or width.

## Uniform-scale feasibility

The original dark-body extremal heights are Gu→Feng `1058, 1214` px and
Feng→Gu `1214, 1093` px. To make each endpoint 200±2 px tall with a single
isotropic scale, the direction's two endpoint intervals must intersect:

| Direction | First endpoint candidate | Last endpoint candidate | 200±2 px scale intervals | Intersection? |
| --- | ---: | ---: | --- | --- |
| Gu→Feng | 200/1058 = 0.189036 | 200/1214 = 0.164745 | [0.187146, 0.190926] vs [0.163097, 0.166392] | No |
| Feng→Gu | 200/1214 = 0.164745 | 200/1093 = 0.182983 | [0.163097, 0.166392] vs [0.181153, 0.184812] | No |

Even before effect fit or centering, one sequence-wide scale cannot align
both endpoints. The nonzero-alpha sequence union widths are 1240 px
(Gu→Feng) and 1218 px (Feng→Gu), yielding additional marginless no-crop
scale ceilings of `192/1240 = 0.154839` and `192/1218 = 0.157635`.
Some extreme alpha is low-opacity source fringe, but Phase 3B does not
authorize deleting or repainting nontransparent content. More importantly,
the endpoint-body scale intervals already fail independently of that fringe.

Suggested **per-endpoint** body scales are recorded only as diagnostic
numbers, not implementation parameters. Using them would violate the
single-scale rule. Shrinking the body to accommodate the sequence would
reproduce the Phase 3A endpoint pop. Cropping significant effects or using
different per-frame scales is outside the user's permitted operations.

## QA artifacts and disposition

- `hatch-runs/transition-qa/endpoints/gu-to-feng-endpoints.png`
- `hatch-runs/transition-qa/endpoints/feng-to-gu-endpoints.png`
- `hatch-runs/transition-qa/endpoints/contact-sheet.png`
- `hatch-runs/transition-qa/endpoints/analysis.json`

Comparison sheets enlarge only with nearest-neighbor. Cyan is the x=96
guide, green is y=203, red is full alpha, and amber is the character proxy.
These are analysis media, not replacement assets. `ENDPOINT_ALIGNMENT_BLOCKED`
is a geometry conclusion; visual review remains required, and the current
Phase 3A runtime derivatives must not be treated as visually seamless.

## Phase 3C — smoothstep schedule and effect-fit preflight

Phase 3C permits per-frame isotropic scaling, but only through one fixed
smoothstep schedule. `tools/derive_transition_scale_schedule.py` rereads the
formal idle body heights (both 200 px) and approved source endpoint dark-body
heights (1058→1214 and 1214→1093 px); no endpoint scale is hard-coded. The
generated diagnostic fixture is
`runtime-patch/fixtures/transition-scale-schedule.json`. Each entry records
frame index, normalized `t`, floating scale, integer nearest-neighbor resize
side, effective raster scale, x=96 body-center target, and y=203 body baseline.

| Direction | Floating smoothstep scales, in frame order | Integer resize sides |
| --- | --- | --- |
| Gu→Feng | 0.189036, 0.188203, 0.185970, 0.182738, 0.178906, 0.174874, 0.171042, 0.167810, 0.165578, 0.164745 | 237, 236, 233, 229, 224, 219, 214, 210, 208, 207 |
| Feng→Gu | 0.164745, 0.165755, 0.168360, 0.171923, 0.175804, 0.179367, 0.181972, 0.182983 | 207, 208, 211, 216, 220, 225, 228, 229 |

Both sequences are monotonic. Nearest-neighbor preflight finds rasterized
endpoint body heights `200→200` (Gu→Feng) and `200→199` (Feng→Gu). All
proposed body baselines are y=203 and integer body centers are x=95.5–96.5.
This matches the requested transition-cell target but not the approved Gu
idle alpha-bbox center x=88; a further 8 px entry/exit registration question
would remain even if effects fit. The formal atlas is not shifted.
The largest adjacent effective-scale changes are about 2.3% and 2.4%, below
the 10% limit. Gu→Feng has one 13 px adjacent body-height change driven by
the original pose (frames 7→8), recorded as `POSE_DRIVEN_DELTA`; Feng→Gu's
maximum is 6 px.

However, the same preflight proves `IMPORTANT_ALPHA_CLIPPED` for approved
Gu→Feng frames 03–08 after character-centered baseline placement. The
high-alpha content (`alpha ≥128`) extends above the 192×208 cell at those
scheduled scales:

| Gu→Feng frame | Predicted important-content top y | Bottom exclusive |
| ---: | ---: | ---: |
| 03 | −16 | 204 |
| 04 | −16 | 208 |
| 05 | −16 | 204 |
| 06 | −11 | 204 |
| 07 | −8 | 204 |
| 08 | −2 | 204 |

Frame 04's opaque effect bbox is 224 px tall after scheduled rasterization,
larger than the entire 208 px cell. No integer translation can keep both
important effect and grounded body inside the cell. This is not faint alpha=1
fringe: the preflight uses only pixels with alpha at least 128. It therefore
triggers the Phase 3C hard stop before overwriting any formal runtime asset.
The complete row-by-row evidence is in
`hatch-runs/transition-qa/schedule/preflight.json`.

`SCHEDULE_DERIVATION_PASS`, but `STRUCTURAL_ENDPOINT_CHECK = BLOCKED` for
runtime application. Commit 1 freezes the diagnostic schedule and preflight;
the planned regeneration and scaled-sequence QA commits must not run while
important effects would be cropped. The existing Phase 3A runtime PNGs and
SHA manifest remain unchanged. `VISUAL_REVIEW_REQUIRED = true`.
