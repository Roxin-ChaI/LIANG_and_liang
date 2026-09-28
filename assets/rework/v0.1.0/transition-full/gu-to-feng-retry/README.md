# Gu → Feng targeted redraw — structure PASS, visual FAIL

Ten independent RGBA192×208 PNGs have exact approved A/B boundary files. Shared
nearest-neighbor normalization, binary alpha and integer registration preserve
the sole203 registration without per-pose fitting. There are no isolated pixels
or cell-edge clipping in this retry. The generated source remains independently
retained in `../sources/gu-to-feng-generated-retry.png`.

**NOT runtime eligible:** independent visual QA rejects08→09: the generated
stance/torso is wider than canonical Feng and abruptly narrows; the round frontal
face cuts to the approved sharper turned face. 00→01 still drops the hair7px
while soles stay grounded;02→03 jumps both hands to the chest. Intended shoulder
strengthening is not itself a failure; boundary convergence is the blocker.

See `qa/contact-sheet.png`, all nine adjacent overlays, `qa/validation.json` and
`qa/independent-review.json`. The successful redraw followed one failed transport
request and one identical transport retry; exact prompt and provenance are in
`../gu-to-feng/generation.json` and `../gu-to-feng/retry-prompt.txt`.

No frames were hidden, accelerated, blurred or programmatically morphed to obtain
a pass. The player, frozen atlas and running App were not changed. Idle actual
App QA and Running endpoint audit remain NOT_TESTED, not approved by this source.
