# Deterministic K1 local pixel candidate

Only K1 is derived from frozen A, following the user's explicit local-edit
authorization. No ImageGen, whole-person fit, interpolation, new colors, effects,
head drawing, K2/K3 replacement, player/Scheduler/Hook change or App integration.

The reproducible pixel plan copies two small lower-arm/hand rectangles1px inward
from immutable A donors, clearing only vacated source-minus-destination pixels.
The change is minute arm tension, not body strengthening. The small adjacent
upper-leg occlusion fragments within those rectangles move with the local copy;
all lower legs/feet, shoulders and torso above y128 stay byte-identical. This is
not claimed to be an anatomical segmentation of arms alone.

## Actual measurements

| Check | A | K1 | Delta |
| --- | --- | --- | --- |
| Head bbox | [54,4,122,84] | exact same | 0 |
| Head size | 68×80 | 68×80 | 0 |
| Head center | (88,44) | (88,44) | (0,0) |
| Shoulder canonical guide | 33 | 33 | 0 |
| Shoulder90:110 hull width | unchanged | unchanged | 0 |
| Body70:208 alpha bbox | [69,70,122,204] | [69,70,121,204] | left0,right-1 |
| Sole | 203 | 203 | 0 |
| Registration anchor | 96 | 96 | no global operation |

The body-band center95.5→95.0 is a silhouette measurement, not a changed
registration anchor. It reflects the tiny local hand adjustment, not a global
sprite move. The conservative locked mask is unchanged from Commit1.

Locked selection:138,980 RGBA bytes,0 different bytes and0 changed locked pixels.
Both SHA256 values are
`61d9eb419f5449d61cad2616bd5154a674c46e9c9b3a58d684adbac614207dc9`.
K1 PNG SHA256:
`3fe2510fce45d2e7fb63e2018f79fe69ef9f05c470634903fa580700acc9e246`.
Changed pixels860, confined to[69,128,122,160]. Alpha0/255 only, hidden RGB0,
isolated pixels0, one connected character, no clipping. Exterior flood confirms
A and K1 each have0 enclosed transparent pixels; no new holes/seams.

## Static review versus art approval

Independent reviewer `locked_k1_visual` returns **A_K1_STATIC_PASS**: identity,
head/neck/proportions, wrist attachments, seams, clearance and continuity pass.
The native-scale charge cue is very subtle and remains a manual artistic choice:
`chargeIntentReadability=unknown`, `USER_ART_APPROVAL=PENDING`. Do not describe
this as human art approval, full-chain approval or runtime QA.

`static-review-resolution.json` recalculates technical QA from actual K1 pixels
and binds the independent review to their SHA256. Only the static PASS opens the
requested read-only A→K1→existing K2 audit. A missing/stale/failed visual check
cannot open that gate. A subsequent bad K2 must not change this near-Gu K1.

Evidence: `assets/rework/v0.1.0/transition-keyframes/k1-locked/candidate/` contains
native `K1.png`, exact A copy, difference mask, overlay, native Contact Sheet,
QA-only nearest3x inspection, landmark report, byte comparison and review.
No extra poses, full animation or App-ready package is emitted.
