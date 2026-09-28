# Transition derived-asset gate — NEEDS_MANUAL_ART_REDESIGN

No low-quality substitute frames have been created. The requested no-redraw gate is reached: safe whole-pose reuse/rigid translation does not reconcile the existing Gu head/face/torso drawings with both canonical state families.

## Tested, not presumed

- All18 frozen oversized transition frames, projected to normal coordinates for diagnosis only, were tested against Gu Idle0 and corrected Gu Running0 at integer dx=-16…16 with vertical placement fixed. No exact whole-pose match exists. Best Idle reuse is reverse7 at dx=-8 (9,874 different RGBA pixels); best Running reuse is reverse7 at dx=-2 (11,149). These counts alone do **not** establish visual failure.
- [Full original ordered stages](reuse/unchanged-source-stages.png) retain all10/8 frames, full oversized canvases, no resize. [Boundary-only substitution diagnostic](reuse/boundary-only-diagnostic.png) compares canonical pixels with the old endpoint and its neighbor; it is **not a playable candidate strip**.
- Forward: replacing only frame0 with canonical Gu leaves the different Gu head/face placement at old frame1. Extending copied canonical poses then meets the grown Feng body at old frame2: the missing pose-matched intermediate cannot be invented by repeating the canonical image.
- Reverse: replacing only final7 with canonical Gu still meets old frame6's different tilted/narrow head, arm/torso pose and stance. Integer alignment changes registration but not facial/pose construction. Copying additional endpoint frames relocates the join, rather than making the shrinking motion converge naturally.
- Idle and Running have distinct approved poses. Forcing Running to Idle at either boundary introduces the very reset prohibited by the new contract. Effect-color masks cannot safely separate blue suit pixels from blue energy, and head/torso splicing, warping or pixel dissolves are not acceptable artwork substitutes.

[Feasibility ledger](reuse/reuse-feasibility.json) freezes all18 input hashes and explicitly records `animationFramesGenerated=false`, `sourceFramesModified=false`, `packagingEligible=false`. This is a bounded evaluation of existing whole-pose reuse and rigid transforms, **not** a mathematical claim that every possible expert pixel-art edit is impossible.

[Independent review](reuse/independent-review.json) agrees that continuous morphing needs intermediate character drawings, with an important qualification: Idle's canonical→old frame1 variant alone is a small visual warning, not a hard fail. Running's head-height change and reverse tilt/stance join are clearer. Intentional expansion/contraction is accepted; static sheets cannot certify optical severity or automatically reject every pixel difference.

## Actual modification scope

- **Gu/Feng standard atlases: zero changes.** Existing Gu registration derivative remains the test input.
- **Original/derived transition animation files: zero changes.** No new runtime-eligible sequence, endpoint swap, hidden frame or accelerated playback was emitted.
- New files are specification references, contact-sheet diagnostics, feasibility data and regression tests only.

Needed manual art work: state-matched Gu entrance0–2 and Gu convergence5–7, with reviewed neighbor poses and authored subject/effect masks; retain10/8 ordered stages. Other stages should remain unchanged unless the continuity review demonstrates they must join differently. Do not begin generation/repainting without a separately approved art-redesign workflow.

Player repair and actual-window testing may proceed independently using the explicitly unchanged transition assets. Such tests cannot be reported as integrated acceptance of new artwork; new-asset integration remains **NOT_TESTED / BLOCKED_ART**. Final verdict must remain VISUAL_QA_FAIL until the endpoint gate is satisfied.
