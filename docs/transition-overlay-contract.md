# Anchored oversized transition overlay contract (Phase 3D)

This is a reference contract and deterministic asset layout, not an installed
Desktop patch. The approved Gu/Feng v2 atlases, source transition PNGs, native
Pet ID, and normal 192×208 renderer box are untouched.

The frozen Phase 3C scale schedule determines one isotropic nearest-neighbor
resize per approved 1254×1254 frame. The opaque dark-character bbox is an
extremal *body proxy* for integer translation, not the renderer anchor.
After translation the body proxy's center is within 1 px of the normal Pet
anchor x=96, and its shoe baseline is exactly y=203. All nonzero-alpha pixels,
including faint effects, determine the overlay canvas; the alpha≥128 extent is
also recorded in `hatch-runs/transition-qa/overlay/preflight.json`.

The fixed per-direction metadata is
`runtime-patch/fixtures/transition-overlay-layout.json`. Canvas dimensions
are the full-alpha union plus the normal Pet reference box, rounded upward to
16 px. A direction exceeding 384×384 blocks asset generation. An overlay frame
contains `{source,width,height,anchorX,anchorY}` or uses sequence-level
`{canvasWidth,canvasHeight,anchorX,anchorY,frames}`. The normal form source
remains its unchanged 192×208 atlas and does not acquire these overlay fields.

The overlay visual's canvas anchor `(anchorX,anchorY)` must map to the normal
Pet coordinate `(96,203)`:

```text
left = petAnchorX - anchorX = 96 - anchorX
top  = petBaselineY - anchorY = 203 - anchorY
```

The normal Pet renderer retains its 192×208 positioning and drag hitbox.
During one-shot transition, a visual-only absolute sibling uses the above
offset, fixed canvas dimensions, `pointer-events:none`, and a clipping-safe
ancestor. On completion the sibling is removed and the already-loaded target
atlas atomically takes over the normal renderer. The native task and look
states are not inserted into the transition sequence.

The existing `assets/transform-runtime/` 192×208 outputs and default
normalization mode remain historical Phase 3A/3B QA assets. New oversized
PNGs live only under `assets/transform-overlay/` and require explicit
`--layout overlay`.
