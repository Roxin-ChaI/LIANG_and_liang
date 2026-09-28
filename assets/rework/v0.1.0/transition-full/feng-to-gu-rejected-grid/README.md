# Feng → Gu source rejected before playable-frame extraction

The built-in generator produced eight complete figures, then one targeted
redraw. Both originals are retained in `../sources/`. This is an **audit
package**, not an eight-frame runtime animation.

The selected retry is1704×923 RGBA. Its figures do not respect the requested
equal4×2 slots: shoes of the first row cross the half-height division into the
second row. Normal192×208 extraction would cut shoes and mix feet into the next
row. `prepare_transition_animation_candidate` refuses that registration rather
than crop pixels or independently resize poses. No playable PNGs were emitted.

`grid-diagnosis.json` records all eight raw-cell boxes and registration failures.
`rejected-grid-contact-sheet.png` intentionally shows the failed raw divisions;
it is **not** a preview of a corrected animation. The first attempt's analogous
diagnosis is in `../feng-to-gu-first-grid/`.

Independent static review also finds that the final generated Gu approximation
does not sufficiently converge to approved D's face and suit. The lowering
hand/narrowing stance is intentional, but cannot excuse endpoint identity drift.
See `independent-review.json`. C/D themselves remain unchanged and user approved
for Idle only. No source is runtime eligible; Idle and Running integration are
NOT_TESTED. Do not package this source as a successful animation.
