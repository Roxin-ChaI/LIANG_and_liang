# Two bridges tested; B_BRIDGE_QA_FAIL_MORE_ART_SCOPE_REQUIRED

KB2 was made only after fresh K3→KB1 static PASS and KB1→B `KB2_REQUIRED`.
It is a second bounded native-pixel derivation, not a new whole character:
KB1's head/identity reference part62×74→56×68 locally with NEAREST,
same center-x88 / center-y41→38, body81→93 (+12), small2px inward/up
forearm onset. Neck/jacket row copies taper into unchanged source rows;
all y164:208 bytes, feet and sole203 remain fixed. Alpha0/255, source palette,
one component, no hidden RGB, clipping, isolated pixels or new enclosed holes.

No B pixels are used as donors. No global fitting, AI regeneration, blending,
antialiasing or effects. Plan and actual PNG/RGBA hashes are retained. Actual
KB2 PNG SHA256:
`622c81f99cde42f5846044a391424e7f4a8afa326d2c5e235470b2cacb618b19`.

## Actual paired results (static, not App playback)

| Pair | Head Δwidth/height | Head center Δx/Δy | Body70:208 Δwidth | Gate |
| --- | --- | --- | --- | --- |
| A→K1 | 0/0 | 0/0 | −1 | Prior user art approval + fresh original technical PASS |
| K1→K2 | 0/0 | 0/0 | +7 | Prior user art approval + fresh original technical PASS |
| K2→K3 | 0/0 | 0/0 | +10 | Prior user art approval + fresh original technical PASS |
| K3→KB1 | −6/−6 | 0/−3 | +12 | Fresh numeric + independent static PASS |
| KB1→KB2 | −6/−6 | 0/−3 | +12 | Fresh numeric + independent static PASS |
| KB2→B | approx−7/−14 | approx+0.5/−7 | +11 | Numeric and independent static FAIL |

All soles203 / registration96; hull center stays94.5 in both bridges and
becomes96 in B. Registration is not an asymmetric silhouette's center. Old
approved A→K1 has a1px body-hull contraction; the new bridge growth-only
budget does **not** retroactively invalidate its original gate or approval.

B's chin is partly hand-occluded; historical head reference49×54 / center
(88.5,31) is approximate with ±3px guide uncertainty. Guides in Gu/bridges
include neck/upper collar, not an exact isolated skull. Body hull is jacket/arm
geometry, not anatomical shoulders. These caveats are retained in every report;
the FAIL is also evident in actual contacts, not just inferred from thresholds.

Independent `bridge_static_visual` inspected each incoming contact, nearest3x
and overlay, then the complete actual chain and outgoing KB2/B pair. KB1→KB2
identity, head, neck/collar, body progression, arm attachment, cloth seams,
fixed feet, artifacts and continuity all PASS. Incoming acceptance does not
make KB2→B continuous.

## Remaining P1 at the frozen B endpoint

The second bridge still has the Gu-side hanging hands and narrow parallel
legs. B suddenly bends the screen-left elbow across the chest to put a finger
at the chin, changes the other hand to a fist, spreads both legs/feet, raises
the shoulder line and changes lapels/jacket/waist and cloth shading together.
The recognizable hair/glasses/face support identity PASS, but arm/pose
continuity FAIL. The smaller/higher head arrives together with those changes.
Body width+11 alone now fits the numeric budget, yet cannot measure or cure
these missing limb, stance and garment stages. No frame hidden or accelerated.

One or two bridge poses are **not sufficient**. Based on the current nominal
head guide, K3→B requires at least five links/four bridges at6px per link.
After KB2 the nominal14px height residual needs three links/two extra bridges.
Approximate annotations and missing pose art mean these are lower-bound
planning calculations, not a claim four frames will visually pass. Additional
KB3/KB4 or manual pose design needs new authorization; none was generated.

Verdict: **B_BRIDGE_QA_FAIL_MORE_ART_SCOPE_REQUIRED**; requested
`B_BRIDGE_ART_APPROVED` is FAIL. No full10-frame fill, runtime eligibility,
App integration, Tag or current-running-version replacement. New bridges
have independent static evidence, not a fabricated human artistic approval.

## QA package, freshness and safety

`assets/rework/v0.1.0/transition-keyframes/k3-b-bridge/full-chain-qa/` contains
seven-pose native/nearest3x contacts, all new adjacent-pair RGBA diff contacts,
landmarks, raw pixel hashes, independent outgoing review and final verdict.
The final gate rechecks actual approved sources, both incoming reviews,
KB2 derivation, all seven landmarks and all pairs; stale or altered reports
cannot authorize completion. No regression fixture is reported as visual QA.

All approved A/K1/K2/K3/B files and earlier QA remain unchanged. Protected-path
comparison to pre-task0ba5f6a is empty for endpoint/keyframe packages, standard
atlas, standalone App, player, Scheduler and authorized Hook. New KB1 and its
plan/QA are unchanged after293477a. No App or Codex runtime was started.

Reproduce with the three new tools and independent stored reviews; generator
commands refuse to overwrite candidates. Run the five bridge Python test
modules; full Python/Node regressions are recorded below after completion.

Final regression before this commit: Python512 PASS,1 existing xfail,
12 subtests PASS; Node216 PASS,0 failed. The five new bridge modules account
for55 focused Python tests. Both staged and unstaged diff checks pass. Tests
exercise historical runtime recipes using test fixtures only, not a real App
patch/launch. Automated PASS does not override the independent visual FAIL.
