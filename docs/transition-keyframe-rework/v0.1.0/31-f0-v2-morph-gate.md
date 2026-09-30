# KF2→F0-v2 Morph gate

Project static verdict: **F0_MORPH_ENDPOINT_APPROVED**. This is the current agent's direct static image review plus hash-bound technical checks, not a user approval or an App motion test.

| Metric | KF2 | F0-v2 | Delta |
| --- | --- | --- | --- |
| Head guide | 52×59 | 50×55 | −2×−4 |
| Head center | 88,33.5 | 88,31.5 | 0,−2 |
| Body-band width | 100 | 101 | +1 |
| Baseline | 203 | 203 | 0 |
| Registration anchor | 96 | 96 | 0 |
| Hand centers | 69,143 / 122,143 | unchanged | 0 |

Geometry is only the first gate. The direct native/nearest-3x review separately passes the head, completed strong-form silhouette, face, arms, pants and jacket channels. KF2's relaxed face persists, the broad blue shoulder/chest mass remains continuous, and the original low hands and straight legs are retained. The smaller head and consolidated upper suit reach the specified neutral Feng morphology without copying the previous F0's sharp face and folded pants.

The facial crop is byte-identical after a 2px upward placement. Hands/cuffs and y≥192 feet are byte-identical at their original coordinates. The basic tailored suit is present; final Idle rendering detail is deferred. The inherited angular elbow shape is not newly redesigned in this step.

Evidence: `assets/rework/v0.1.0/transition-keyframes/feng-f0/v2/morph-gate/visual-review.json`, `gate.json`, `semantic-contact-sheet.png`, plus the candidate Contact Sheet and overlay. Review provenance identifies the actual reviewer; no independent human approval is claimed.

This verdict permits only the requested F0-v2→B Entry audit. It does not authorize App integration or generated Entry frames. A stale source/candidate hash, any failed semantic channel, or any failed byte lock blocks the gate even when the other geometry checks pass.
