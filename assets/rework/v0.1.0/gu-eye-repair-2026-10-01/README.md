# Gu eye-only repair candidate — human review required

Not installed, not approved, and not a replacement for the formal atlas.

Source: baseline-corrected `assets/rework/v0.1.0/gu/spritesheet.webp`.
All six edited frames retain baseline y=203. Frame numbering below starts at 01.

- failed 02: viewer-left eye only (the opposite eye is unchanged).
- failed 08: both eyes.
- waiting 02, 03, 05, 06: both eyes.

The user explicitly approved deterministic local pixel editing instead of ImageGen.
Each patch copies RGB from a 10×5 canonical Gu Idle eye region without scaling,
interpolation, quantization, or generated pixels. Original destination Alpha is
preserved. Patch positions follow each frame's existing eye locations.

Eyes occupy only the masks in `qa/*-allowed-mask.png`; unchanged bytes outside
those masks include glasses rims/bridge, eyebrows, face silhouette, hair and body.
Changed pixels: 50, 100, 100, 100, 100, 99 respectively. These are technical
containment checks, not proof of anatomical or animation quality.

## Review

- `qa/failed-before-after.png` / `qa/waiting-before-after.png`: before / candidate / difference, 6× nearest-neighbor detail.
- `qa/failed-before-after.gif` / `qa/waiting-before-after.gif`: full-state before/after loop.
- `failed.png` / `waiting.png`: complete review strips; unlisted frames unchanged.
- Six individual PNGs and the JSON report retain exact native pixel information.

Review pupil shape, eyelid height, gaze alignment and continuity between frames.
Canonical eye reuse may reduce the original side-glance in waiting 02/03; this
needs explicit visual acceptance and must not be silently declared fixed.

Existing Waiting facial alpha values 253/254 remain unchanged and are outside
this eye-only patch. GIFs are composited on a dark background and palette-limited
for preview only; source PNGs are never reconstructed from those GIFs.

Status: `CANDIDATE_REQUIRES_USER_VISUAL_REVIEW`. Stop on visible deformation.
