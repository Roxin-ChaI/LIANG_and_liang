# KB1→B: KB2_REQUIRED (not BRIDGE_COMPLETE)

This read-only gate runs only after fresh K3→KB1 static PASS. It re-reads
actual frozen A/K1/K2/K3/B, pinned KB1 and the independent incoming review.
No new image pose, source modification or App integration occurs in this stage.

| Remaining landmark | KB1 | Frozen B | Delta |
| --- | --- | --- | --- |
| Head reference size | 62×74 | approx49×54 | −13 / −20 |
| Head reference center | (88,41) | approx(88.5,31) | +0.5 / −10 |
| Body70:208 bbox | [54,70,135,204] | [44,70,148,204] | left−10 / right+13 |
| Body reference width | 81 | 104 | +23 |
| Body-band center | 94.5 | 96 | +1.5 |
| Sole / registration | 203 / 96 | 203 / 96 | 0 / 0 |

B head guide remains ±3px / hand-occluded, not exact anatomy. Independent
review confirms the visible head/chest/limb jump even with that uncertainty.
The same hair/glasses identity is recognizable, but arm-pose continuity FAIL:
KB1's left hand remains at the hip; B's left elbow bends and forearm crosses
the chest to bring a finger to the chin. Right arm becomes broader and fist-like.
Legs/feet spread and jacket shading/lapel/waist construction change together.
These are missing pose stages, not problems solved by a constant baseline.

For scale of the arm gap (semi-automatic visual annotation, not a gate): KB1
left-hand skin hull in native ROI x50:90/y130:164 is [74,141,82,156] (center
78,148.5). B's finger/palm is visually about [74,50,91,82] (center82.5,66),
with roughly±3px uncertainty and face overlap. The hand-envelope center rises
about82.5px, not the1px onset in KB1. This illustrates the missing bend/lift
language; it is not a precise wrist joint measurement or a promised arm path.

Verdict **KB2_REQUIRED**. The incoming KB1 limits stay unchanged. KB2 may be
derived within the same local budgets; nominal capacity already warns its
outgoing link may remain FAIL. Never modify approved K3/KB1/B to make that
link appear smaller, never synthesize KB3+ without authorization, and never
label numerical/identity PASS as pose-continuity PASS.

Evidence in `k3-b-bridge/kb1-b-gate/`: actual native/nearest3x pair and full
A/K1/K2/K3/KB1/B contacts, diff overlay, measured residuals, independent
hash-bound verdict. Tests exercise stale/missing incoming/outgoing reviews,
altered cached metrics, changed KB1 and numeric limits that visual review
cannot override. Static QA is not user art approval; full-animation fill blocked.
