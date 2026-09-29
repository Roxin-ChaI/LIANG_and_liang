# K1→controlled K2→existing K3: K3_REWORK_REQUIRED

Only after the final K2's exact pixels passed both local-byte/geometry checks
and fresh independent static review did this conditional read-only chain audit
run. No K3/frame/animation/App was generated. K1, final K2, K3 and B are unchanged.

## Verdicts remain separate

- User-approved source: K1_ART_APPROVED (explicit current user statement).
- K1→new K2 numerical and independent static continuity: PASS.
- New K2 user art approval: PENDING; no false `K2_ART_APPROVED` human claim.
- New K2→existing K3: P1 K3_REWORK_REQUIRED, independent static FAIL.
- Whole keyframe chain: still KEYFRAME_QA_FAIL; no full animation/runtime approval.

## Actual next-step comparison

| Landmark | New K2 | Existing K3 | Delta |
| --- | --- | --- | --- |
| Head size | 68×80 | approx52×58 | approx-16×-22 |
| Head center | (88,44) | approx(90,33) | approx(+2,-11) |
| Upper shoulder guide | 33,y83 locked | approx70,y65:67 | approx+37; differing heights |
| Cap84:100 alpha hull | 59 | 101 | +42 |
| Body70:208 bbox | [65,70,124,204] | [45,70,149,204] | left-20,right+25 |
| Body-band width | 59 | 104 | +45 |
| Sole | 203 | 203 | 0 |

Historical K3 anatomical annotations have about±3px uncertainty; they are not
new exact segmentation. The upper guide rows differ, and the cap hull is NOT
anatomical shoulder width. Both are reported without treating an8px lower-cap
expansion as an8px skeletal measurement. The exact body/cap band comparisons
use the same rows. A42px cap-band increase is distinct from45px overall body
width increase; hand/stance extrema need not fall in the shoulder band.

Independent native/nearest3x visual review confirms more than a metric change:
K3 abruptly reduces/raises the head and sharpens the face, broadens muscular
chest/arms/hips, spreads the leg stance and changes both hands/arm pose together.
Its brighter suit/folds further shift visual balance. Keeping sole203 does not
repair this conspicuous redesign. The modest K1→K2 local jacket step remains
continuous, so do NOT widen or shrink the new K2 to accommodate old K3.

## Evidence and protected scope

`assets/rework/v0.1.0/transition-keyframes/k2-controlled/chain-qa/` contains
native and QA-nearest3x Contact Sheets, K1/K2 and K2/K3 RGBA overlay contacts,
landmark report, independent hash-bound review and final verdict.
The final candidate is only `candidate-locked-hands/K2.png`; the earlier
`candidate/` package is explicitly rejected draft evidence.

K2 PNG SHA256:
`565122ea1364eebd56a0d6d3b53934bef8d45d53cb1787eedf4ee1f812cdfcec`.
K3 unchanged PNG SHA256:
`bf2ce6f91fd6a545ffaec47b82227b55e9ae7d19d69ffcbd2e9e6a322f934314`.
Fresh/missing/stale review tests ensure a numerical PASS alone cannot open this
audit or claim a visually verified verdict. Replay fixtures are labelled test
fixtures; they do not replace the actual independent PNG reviews.

Stop here. Next work requires a separately authorized intermediate K3 redesign
and human review, not edits to approved K1 or reviewed new K2. No extra animation
frames, App integration, player/Scheduler/Hook changes, current-App replacement,
standard atlas edits or Tag. The protected-path Git comparison against9c5e1ec
is empty for A/B, all k1-locked files, old K2/K3, both standard atlases,
standalone-app, transition player and authorized Hook definitions.

Validation before this commit:58 focused pixel/constraint/chain tests passed;
full Python420 passed,1 historical xfail,12 subtests passed; Node216 passed,
0 failed. All Git unstaged/staged whitespace checks pass. These regressions do
not convert the observed K3 visual FAIL to a PASS or grant human art approval.
