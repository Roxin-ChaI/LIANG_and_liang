# Gu → Feng candidate — rejected, NOT runtime eligible

Ten independent 192×208 RGBA PNGs are retained in `frames/` **as failed audit
evidence**, not a completed approved animation. Frame00 is byte-identical to A;
frame09 is byte-identical to B. Eight middle poses came from one coherent
image-generation call, not a procedural morph, dissolve, warp or repeated tile.

One shared nearest-neighbor sheet normalization, binary alpha hardening and
integer registration were used. Per-pose fitting/resizing was not used. All
soles reach203 and body-band centers are95.5–96.5, but this is insufficient:
00→01 visibly lowers the head7px and08→09 changes facial/pose relationships.
Frame02 also retains an unintended single pixel rather than silently hiding it.

See `qa/contact-sheet.png`, nine `qa/adjacent-*.png` overlays, numerical
`qa/validation.json` and `qa/independent-review.json`. Fixed head/body bands are
QA references, not anatomical segmentation. The independent reviewer rejects
this candidate. The targeted art correction first failed with a transport
connection error and yielded no new source. One identical transport retry then
succeeded; its extracted ten frames and separate failed final review are in
`../gu-to-feng-retry/`. No alternative generation path or code-generated
substitute was used.

Original successful source is `../sources/gu-to-feng-generated.png`. No player,
atlas, Scheduler, Hook or currently running App has been changed. Actual App
integration is NOT_TESTED; Running approval is not inferred from Idle endpoint
approval. This directory must not be packaged or installed.
