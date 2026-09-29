# A→locked K1→existing K2: K2_REWORK_REQUIRED

The audit ran only after actual K1 pixels passed the byte/geometry gate and
independent A→K1 static continuity review. No candidate was generated or modified
by this stage. K2 SHA256 remains
`057eb3762789c5b388e09063180279a6043ceeed55a20db4e53f7661e9130c37`.
K3 remains unchanged and is not re-reviewed.

## Separate verdicts

- Locked head/identity bytes: PASS,0 different bytes.
- A→K1 constraints and independent static continuity: PASS.
- K1 charge cue and user art approval: MANUAL_VISUAL_QA / PENDING.
- K1→K2: **P1 K2_REWORK_REQUIRED**.
- Whole keyframe chain: KEYFRAME_QA_FAIL, no animation/App approval.

## Observed next discontinuity

| Landmark | New K1 | Existing K2 | Delta |
| --- | --- | --- | --- |
| Head size | 68×80 | approx55×59 | approx-13×-21 |
| Head center | (88,44) | approx(95.5,34.5) | approx(+7.5,-9.5) |
| Shoulder guide width | 33 | approx62 | approx+29 |
| Body70:208 alpha bbox | [69,70,121,204] | [53,70,139,204] | (-16,0,+18,0) |
| Sole | 203 | 203 | 0 |

K2 anatomical guides are the earlier independent annotations, uncertainty about
±3px, not newly derived exact segmentation. The guide delta is now+29 rather
than the previous+27 because the corrected K1 retains Gu's width33 instead of
the earlier width35. Body-band bounds and soles are separate exact alpha metrics.

Independent review confirms the failure in real native PNG comparisons, not
only metrics: K2 simultaneously shrinks/raises/shifts the head and widens the
chest, shoulders, arms and stance. The hand pose is independently plausible,
but the head/body proportion change creates a conspicuous key-to-key redesign.
Baseline stability does not repair that. This is STATIC evidence, not App video
or a claim about actual transition frame timing.

## Evidence and next scope

`assets/rework/v0.1.0/transition-keyframes/k1-locked/chain-qa/`:
native Contact Sheet, QA nearest3x, A/K1 and K1/K2 overlay panels, landmark report,
independent review and final verdict. No copied/repainted K2 playable frame.

Stop at K2_REWORK_REQUIRED. Keep the new near-Gu K1 fixed; do not strengthen it
to accommodate K2. A future separately authorized K2 rework must preserve face
identity and distribute head/shoulder/body changes gradually. No extra frames,
K3 modifications, player/Scheduler/Hook changes, App integration or Tag here.

The explicit user local-pixel mandate overrides hatch-pet's usual ImageGen
generation policy. Its independent static visual gate is retained: numerical
PASS never substitutes for art approval. The very subtle K1 charge cue remains
for the user to review, even though its identity/continuity checks pass.

Regression: full Python388 passed,1 historical xfail,12 subtests passed;
Node216 passed,0 failed. Static pixel tests do not substitute for user art
approval or actual App QA. The protected-path Git comparison againstc817836
remains empty for A/B, existing K2/K3, standard atlases, player, Scheduler,
standalone App and Hook definitions. Every component is independently committed
after corresponding tests and staged/unstaged diff checks.
