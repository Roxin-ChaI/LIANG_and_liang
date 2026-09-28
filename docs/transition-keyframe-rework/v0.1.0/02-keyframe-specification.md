# A → K1 → K2 → K3 → B specification

Only three new poses are specified. No full10-frame animation, in-betweens,
App integration, player/Scheduler/Hook changes or standard atlas changes.
A/B remain the exact human-approved Idle canonical endpoints.

## Registration and anatomy

192×208 RGBA; x registration96; sole203. These anchors are not a command to
move every anatomical center to x96: Gu's head is approximately x88 and
Feng's x88.5. Preserve that offset and the shared hair-top y4. Abruptly shifting
the face toward96 was one source of previous entry discontinuity.

Manual head guides: Gu[54,4,122,84], Feng[64,4,113,58]. Gu jaw approximately
y78–84; Feng y54–60, partly hand-occluded. These are explicit approximate
visual ROIs, not pixel-perfect anatomical masks. The old head0:70 reference
band excluded Gu's lower jaw and included Feng's shoulder/hand. Use the
anatomical guide AND face inspection, not that band as a head-size certificate.
Manual shoulder guides: Gu(75,83)–(108,83), Feng(60,65)–(128,65); they are
pose-dependent jacket/acromion references, not total arm/stance alpha width.
Full/head-cap/body-band bounds are separately preserved in the JSON.

## Three key poses

| Pose | Intended change | Approx head bbox target | Shoulder-guide width | Body70:208 band width |
| --- | --- | --- | --- | --- |
| K1 | Still Gu; tiny straightening/charge; hands just begin moving | [55,4,122,81] | 33–40 | 53–61 |
| K2 | Intermediate torso/shoulders; gradually widen stance, lift hand | [59,4,118,71] | 46–55 | 70–86 |
| K3 | Near B body/face-angle/hand-at-chin, no overshoot | [63,4,114,61] | 62–68 | 95–104 |

All head centers should remain approximately x86–91, hair tops y3–6, sole203.
These are review budgets, not permission to deform source raster pixels to
fit numbers. The character's head proportions gradually approach Feng;
do not drop the hairline, swap faces, invent round frontal eyes or overgrow
the body before B. Hands travel continuously from Gu rest to Feng chin pose.
Full bbox equality is NOT required for naturally different poses.

Keep black hair, thin glasses, face identity, suit/shirt palette and hard pixels.
Prefer no effects for keyframe approval. Any accent must be small, attached,
hard-edged and outside the face/glasses/main torso/feet; never hide geometry
with glow, blur, energy clouds or detached noise.

## Candidate gate

Review exactly A→K1, K1→K2, K2→K3, K3→B, with head-center/hair-top deltas,
baseline, body bbox, shoulders, face identity, pose/hand/leg continuity and
visual center. Metrics are evidence, not human visual approval. An obvious
snap remains `KEYFRAME_QA_FAIL` even if structural tests pass.

Until user approval, no `KEYFRAME_ART_APPROVED`, no remaining five frames,
no App integration. Running remains unapproved. No previously rejected
whole-row retry is reused as approved K art.

Machine specification and QA-only guides:
`assets/rework/v0.1.0/transition-keyframes/gu-to-feng-spec/`
