# Feng left walk — approved artwork

## User approval — 2026-10-23

The user approved the eight-frame GIF with “审核通过”. Current status:
`FENG_LEFT_WALK_ART_APPROVED`. `review-status.json` records the approval and
freezes all 16 existing artwork, preview and validation files by SHA256.
No pixels, frame order or timing changed. App integration remains out of scope.
The pre-approval validation report and review observations below are retained
unchanged as historical evidence, not a claim that App testing has occurred.

## Construction and pre-approval review

User requested horizontal mirroring of the approved eight-frame right walk.
Source: `assets/rework/v0.1.0/feng-walk-right-eight-2026-10-23/review-r2/`,
approved and frozen in commit `54fe552`.

Output: `assets/rework/v0.1.0/feng-walk-left-eight-2026-10-23/`.

- `left-01.png` through `left-08.png`: exact native RGBA per-frame reflection.
- `feng-running-left.png`: 1536×208, eight 192×208 cells, original temporal order.
- `preview.gif`: 140ms/frame; `preview-slow.gif`: 450ms/frame.
- `preview-native.gif`: native-size review; `contact.png`: all eight poses.
- `right-left-comparison.gif`: approved right on the left, new left on the right.
- `right-left-contact.png`: same pairs; `validation.json`: provenance and hashes.

Reflection is x→191−x within each cell, never across the whole strip. No ImageGen,
redrawing, resampling, color changes, translating or anatomy edits. A source pixel
at x=96 maps to x=95 around the cell axis95.5; no extra shift is added. Every sole
baseline stays y=203. Native PNGs have binary alpha and zero RGB under transparent
pixels. GIFs have a dark review background only; production PNGs remain transparent.

Static self-review: all eight poses face left; hair, face, glasses, arms, cuffs,
hips and shoes retain their approved source shapes under reflection. No new
mirroring-related crop or joint break was observed. No text or one-sided prop
requires correction. The source's accepted height/phase variations remain; this
operation does not claim to repair them. Every adjacent pixel-difference mask,
including 08→01, is exactly the corresponding mirrored source difference mask.

Structural validation: PASS. Human art approval: PENDING. App integration: false;
App test: NOT_TESTED. Animated screen observation: NOT_VERIFIED; GIFs are supplied
for user review. No right sources, Gu art, atlases or runtime settings changed.

Related Python regression: 101 tests passed. `git diff --check` passed.
Scope: left/right walk safeguards, approved key poses, Gu suspended directions,
Feng Look and Failed. This is not a claim of full project Python/Node regression.
