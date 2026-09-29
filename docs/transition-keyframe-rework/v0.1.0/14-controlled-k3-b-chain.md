# K2→new K3→frozen B: B_TRANSITION_BRIDGE_REQUIRED

This read-only conditional audit ran only after the new K3 passed actual
locked-byte/geometry checks and independent incoming static review. No bridge
frames or complete animation were made, and no App was integrated or started.

## Separate verdicts

- K1/K2: current user ART_APPROVED; source PNGs and historical QA unchanged.
- New K3 technical and K2→K3 independent static review: PASS.
- K3→frozen B independent static review: FAIL, P1 endpoint gap remains.
- Combined gate: **B_TRANSITION_BRIDGE_REQUIRED**, not K3_ART_APPROVED.
- K3 user artistic sufficiency: still pending, not forged by static QA.
- Full transition / runtime / release: not approved; no Tag.

Keep K1/K2/new K3/B untouched. Do not enlarge/shrink/repose K3 to absorb B's gap.

## Landmark distribution and outgoing gap

| Landmark | Approved K2 | New K3 | Frozen B |
| --- | --- | --- | --- |
| Head size | 68×80 | 68×80 | approx49×54 |
| Head center | (88,44) | (88,44) | approx(88.5,31) |
| Body70:208 bbox | [65,70,124,204] | [60,70,129,204] | [44,70,148,204] |
| Body-band width | 59 | 69 | 104 |
| Cap84:100 alpha hull width | 59 | 69 | 100 |
| Upper shoulder guide | 33,y83 locked | 33,y83 locked | approx68,y65 |
| Sole / registration | 203 / 96 | 203 / 96 | 203 / 96 |

Incoming body/cap growth is10px, rather than the obsolete45px body jump.
The outgoing body width still increases35px (left16,right19); cap band grows
31px. Head size falls approximately19×26px and head center rises13px with
only0.5px horizontal change. Body-band center changes94.5→96 (+1.5), while the
canvas registration remains96. Baseline stability does not imply pose stability.

B head/shoulder references are historical manual annotations with about±3px
uncertainty; its chin is partly hand-occluded. They are not exact segmentation.
The locked upper shoulder guide at y83 and B's guide at y65 differ in height;
the cap hull is a same-band jacket/arm proxy, **not skeletal shoulder width**.
All measurements remain evidence, not an automatic visual verdict.

## Independent visual findings

Native and QA-nearest3x contact/overlay review confirms a conspicuous exit snap:
the big-headed slender figure changes to a smaller-headed, much broader figure;
the screen-left arm bends up to the chin; both legs/feet spread; the chest,
upper arms and brighter blue suit shading arrive together. Recognizable hair,
glasses and clothing cues persist, but facial proportions and expression change
abruptly. A similar horizontal center and sole203 cannot remove these combined
proportion, limb and shading changes. The incoming restrained jacket expansion
remains continuous and is not invalidated just because B is farther away.

Additional intermediate bridge artwork is required, subject to separate
authorization and art review. Number/poses/pacing are **not specified or
approved** by this audit. No automatic bridge generation or full10-frame fill.

## Evidence / reproducibility / protected paths

`assets/rework/v0.1.0/transition-keyframes/k3-controlled/chain-qa/` contains
native and nearest3x contacts, K2/K3 and K3/B RGBA overlay panels, measured report,
independent hash-bound review and final verdict. Finalization re-reads current
K3 pixels, B, approved K2 and the incoming review, rejecting stale evidence or
changed sources before recording a verdict. Fixtures cannot substitute for the
actual independent visual report; tests label synthetic reviews TEST FIXTURE.

K3 PNG SHA256:
`2b5651503d4d223d5c670152a1425ebafd6d55b5802f55794c6c70b3624876f6`.
B unchanged PNG SHA256:
`4ae8848d3a40e6c3d8507b7fda119d58462f3236b3202471239ee0b9c0ac506b`.

Protected-path Git comparison against24ddaac is empty for approved A/B, all
k1-locked/k2-controlled files, historical failed K2/K3, standard Gu/Feng atlas,
standalone App, player, Scheduler and Hook definitions. New K3 candidate and
edit plan also have no changes afterad2eee5. Only QA documents/code/new art were
added. No App integration, version replacement, Codex runtime patch or Tag.

The explicit user local-pixel mandate overrides normal hatch-pet ImageGen
generation; its independent visual gate influenced the outcome: numerical and
regression PASS do not override the real static K3→B FAIL.

Validation before this stage commit:37 focused K3 constraint/derivation/chain
tests PASS; full Python457 PASS,1 historical xfail,12 subtests PASS; Node216
PASS,0 failed. Every stage has independent commits after corresponding tests
and both staged/unstaged diff checks. A clean working tree is not a visual PASS.
