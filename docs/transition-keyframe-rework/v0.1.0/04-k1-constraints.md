# K1-only constraint tightening

Supersedes only the earlier K1 target. A/B, existing K2/K3 and all historical
evidence remain unchanged. No new candidate is generated in this commit.

K1 is still unmistakably Gu: only start charging / straighten very slightly.
It is not an early head-shrinking or body-growing transformation pose.

| Check | Frozen A reference | K1 hard acceptance |
| --- | --- | --- |
| Anatomical head bbox | [54,4,122,84],68×80 | width65–69,height77–81 |
| Head center | (88,44) | each axis delta at most2 |
| Sole | 203 | exactly203 |
| Shoulder guide width | 33 | absolute change at most4 |
| Body70:208 alpha band | [69,70,122,204] | left and right change each at most3 |

Half-open integer pixel coordinates. Head/shoulder annotations must come from
independent pixel-level visual inspection, not target boxes guessed onto the
picture. The body band is a fixed geometric proxy, not head or torso anatomy.
Annotation uncertainty >1px cannot establish a2px boundary: mark NOT_VERIFIED.
The upper-head alpha extent must also be contained by the annotated head box.

Any hard limit failure is immediately K1_QA_FAIL. Face identity, unchanged
neck length, still-Gu proportions, no premature Feng, pose continuity and
no clipping need separate independent pass/fail/unknown judgments. Numeric
PASS with unknown visuals is never A_K1_PASS. No face reshaping, skull shrink,
neck stretching or effects hiding silhouette differences are allowed.

Processing policy: no whole-character fit/scale, warp, interpolation or
procedural pose synthesis. A sparse1024×1024 edit reference may contain exact
unscaled canonical pixels at fixed slot(416,408)-(608,616). Only native192×208
outputs or that exact1024×1024 layout are accepted. Fixed crop preserves pixel
coordinates; no bbox-driven recentering or zoom is attempted. Foreground outside
the canonical slot fails instead of being cut or resized. This changes input
composition, not character scale. Any alpha hardening must be disclosed.

At most2 single-K1 attempts. No K2/K3 generation and no extra frames. A_K1_PASS
only opens the conditional A→K1→existingK2 audit; it does not approve the chain,
Running, full animation or runtime integration. A bad K2 must not force K1 out
of these bounds. K2_REWORK_REQUIRED is an allowed stop result.

Machine contract:
`assets/rework/v0.1.0/transition-keyframes/k1-only/specification.json`
Gate: `tools/validate_transition_k1.py`.
