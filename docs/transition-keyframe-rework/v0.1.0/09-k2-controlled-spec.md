# K2 controlled-region contract (specification only)

The user explicitly approves the locked-pixel K1 in this task. Its PNG is pinned
to `3fe2510fce45d2e7fb63e2018f79fe69ef9f05c470634903fa580700acc9e246`.
Old K1 QA records are historical and unchanged. A/B, K1, existing K2/K3 and the
two standard atlases stay untouched; a new candidate gets a separate package.

## Geometry and identity

| Constraint | K1 reference | New K2 limit |
| --- | --- | --- |
| Canvas / registration | 192×208 / x96 | unchanged; no registration transform |
| Sole | y203 | unchanged |
| Head guide bbox | [54,4,122,84],68×80 | user ±4px; local method stricter: exact pixels |
| Head center | (88,44) | user ±3px; local method stricter: (0,0) delta |
| Upper shoulder guide | (75,83)→(108,83),width33 | locked as part of upper84 rows |
| Shoulder-cap alpha hull | band84:100 | growth2–12px; not anatomical shoulder width |
| Body70:208 bbox | [69,70,121,204] | each edge expands at most6px, center delta≤1px |

Registration is a canvas anchor, not the head center or alpha-hull center.
The existing Gu head legitimately has x88 center, and body-band center is x95.
Do not translate the character to make either metric equal x96.

The old shoulder guide at y83 belongs to the conservative head/collar boundary.
We keep it exact. A separate band84:100 measures the lower shoulder-cap/upper-arm
silhouette, **not bone-to-bone anatomy**. Both values are reported. Independent
review must confirm plausible gradual shoulders, rather than redefining a bbox
to manufacture a numerical PASS. The actual anatomical growth budget remains
≤12px; the alpha cap proxy is an additional conservative automatic gate.

## Local edit allowance

Whole y0:84 including transparent RGB/alpha, neck/collar x84:103,y84:101,
lower body/hands/feet y146:208 and everything outside x63:129,y84:146 are locked.
New masks and QA live under `transition-keyframes/k2-controlled/spec/`.
No candidate is made by the specification command.

Only native upper-jacket/upper-arm pixels may be moved by small bounded integer
offsets. Cloth seam completion must use documented original K1 RGBA donors.
No whole-person/whole-side scaling, interpolation, global translation, AI
generation, skin/face repaint or effect overlay. Feet, hands and leg stance
remain fixed. No energy effect is needed to demonstrate the small thickening.
Maximum6px body-edge allowance is an explicit conservative local limit, not an
instruction to use all of it or accommodate the obsolete larger K3.

Checks cover source hash, locked bytes including transparency, native RGBA,
head geometry, sole, cap growth, body edges/center, original palette, binary
alpha, zero hidden RGB, connected silhouette, no clipping/isolated pixels or
new enclosed transparent holes. A numerical PASS only opens independent static
review. Human art approval and App eligibility remain separate and pending.
Any failure stops conditional chain QA. If the local posture cannot be made
plausible without relaxing identity, use `MANUAL_PIXEL_ART_REQUIRED`.

The user's explicit controlled pixel-edit method overrides hatch-pet's usual
ImageGen workflow; its independent final visual gate is still retained.
No new K3, remaining animation frames, App integration, player/Scheduler/Hook
edits or Tag are allowed in this scope.
