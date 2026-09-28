# Keyframe candidate gate: KEYFRAME_QA_FAIL

Only A/K1/K2/K3/B were compared. Built-in ImageGen generated the coherent
three-K strip and one targeted repair; no full10-frame animation, remaining
five frames, reverse redraw or App integration. No CLI or procedural character
synthesis. Frozen A/B are byte-exact copies in BOTH candidate packages.

## Extraction versus art approval

Reverse8 source extraction: PASS, source shoes complete; user-authorized common
nearest-neighbor scale200/475, no per-frame scaling. This is NOT reverse art
approval: source03→04 loses about20 px height, and07 is not canonical D.
See `01-extraction.md` and the independent review there.

## Three-key attempt and targeted repair

First attempt concentrated anatomy and hand change too early: Gu head68×80
became approximately56×65 at K1; hand already reached chest and K2 chin.
Independent static-only review returned warnings/awaiting manual approval;
that original verdict is retained verbatim in spirit with its annotations.
Parent's separate constraint resolution rejects it because the committed K1
Charge specification means tiny change while still near Gu, not arbitrary
one-third-progress anatomy. No claim of actually observed App playback is made.

The bounded repair improved rest→chest→chin hand progression. Its independent
review, now including explicit stage semantics, still returns KEYFRAME_QA_FAIL:

- P1 `K1_PREMATURE_HEAD_SHRINK`: A head68×80 → K1 approximately57×68. Head top
  remains nearly fixed(4→5), but face/head shrink11×12 px before torso growth.
  This is not the intended small Charge change. No code/scale hack hides it.
- P2 `K2_SMALL_HEAD`: midpoint head about55×59; recheck when K1 is redesigned.
- P2 `HEAD_CENTER_DETOUR`: head goes right at K2 then left at K3. Stable soles
  do not prove head continuity.
- K3→B: static visual convergence PASS, not full animation or Running approval.

## Final five-pose measurements

All head/shoulder measurements below are independent manual anatomical
approximations, about +/-3px, not segmentation truth. Body bbox is the separate
70:208 alpha reference band, not torso-only anatomy. Registration remains96;
body-band visual center is naturally pose-dependent.

| Key | Approx head bbox | Head center | Shoulder guide width | Body-band bbox | Sole |
| --- | --- | --- | --- | --- | --- |
| A | [54,4,122,84] | (88,44) | 33 | [69,70,122,204] | 203 |
| K1 | [63,5,120,73] | (91.5,39) | 35 | [66,70,122,204] | 203 |
| K2 | [68,5,123,64] | (95.5,34.5) | 62 | [53,70,139,204] | 203 |
| K3 | [64,4,116,62] | (90,33) | 70 | [45,70,149,204] | 203 |
| B | [64,4,113,58] | (88.5,31) | 68 | [44,70,148,204] | 203 |

| Pair | Head center delta(x,y) | Body bbox delta(l,t,r,b) | Shoulder width delta | Sole delta | Independent visual |
| --- | --- | --- | --- | --- | --- |
| A→K1 | (+3.5,-5) | (-3,0,0,0) | +2 | 0 | FAIL |
| K1→K2 | (+4,-4.5) | (-13,0,+17,0) | +27 | 0 | warning |
| K2→K3 | (-5.5,-1.5) | (-8,0,+10,0) | +8 | 0 | warning |
| K3→B | (-1.5,-2) | (-1,0,-1,0) | -2 | 0 | pass |

## Evidence and reproducibility

`assets/rework/v0.1.0/transition-keyframes/gu-to-feng-candidate-retry/`

- `keys/A.png`, `K1.png`, `K2.png`, `K3.png`, `B.png`: exactly five keys.
- `qa/contact-sheet.png`: unobstructed normal-size five-pose comparison.
- `qa/registration-guide.png`: x96 and sole203 QA guides.
- `qa/manual-landmark-contact-sheet.png`: independent head/shoulder annotations.
- `qa/pair-1.png`…`pair-4.png`: actual pixel overlays, no blended character art.
- `qa/landmark-comparison.json`: all pair deltas and independent verdicts.
- `qa/validation.json`: structural PASS, visual FAIL, runtimeEligible=false.
- `qa/independent-review.json`: uncropped/identity/pose review and uncertainty.

First attempt retained at `gu-to-feng-candidate/`; raw sources/provenance at
`sources/`; prompt set is linked there. A single NN scale per generated strip,
integer registration and binary-alpha hardening only. No per-pose warp/resize.
No image content is altered to meet measured landmarks.

## Stop gate and next art action

Stop here. No KEYFRAME_ART_APPROVED, remaining five frames, App integration,
player/Scheduler/Hook changes or Tag. A/B/C/D and both standard atlases remain
unchanged. Next art work should preserve A-like head proportions through K1,
then gradually change them around K2; keep head lateral movement monotonic.
The next candidate must again be visually reviewed and approved by the user
before any full animation. Running remains NOT_APPROVED.

Actual App/Running/playback QA: NOT_TESTED by design (user forbids integration).
Structural tests cannot replace this art gate.

## Final regression and protected files

- Targeted extraction/specification/candidate/endpoint tests:20 PASS.
- Full Python:335 PASS,12 subtests PASS,1 pre-existing expected failure. That
  expected failure documents the old frozen formal Gu work-row baseline, not
  a new regression; the approved derived Gu correction remains unchanged.
- Full Node:216 PASS. The initial sandbox run could not bind temporary sockets
  (EPERM); rerunning with the bundled Node and authorized test socket access
  passes all216. No actual App test is substituted by these regressions.
- Frozen18 transition-overlay checksums all OK.
- Gu/Feng standard atlas hashes, A/B/C/D, player, renderer, Scheduler and
  authorized Hook definition unchanged against starting commit1716e09.
- Selected ImageGen originals were removed only after exact SHA256-copy
  verification; both source attempts and all evidence remain in this project.

All three staged components are independent. No Tag, App replacement,
new full animation, runtime patch or Hook/config change occurred.
