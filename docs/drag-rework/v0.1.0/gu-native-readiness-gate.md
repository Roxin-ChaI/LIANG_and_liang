# Gu side-shuffle: native readiness gate

Date: 2026-10-01. User approved the four-pose **motion**, not a relaxation of
the canonical Idle appearance contract. Motion approval remains in effect.

## Result

`NATIVE_ART_GATE_FAIL_MOTION_APPROVAL_RETAINED`.

The generated source is 2172×724 with 453,863 partially transparent pixels.
Nearest-neighbor resizing samples these alpha values; it does not make them
binary or restore canonical face, glasses or pixel structure. The displayed
comparison shows differences in face outline, glasses and upper-body rendering.
These are visual observations, not automatically measured anatomical landmarks.

No production frame was created. No alpha threshold, color quantization of PNG
art, per-frame scale fitting, head transplant or identity repair was performed.
The source, canonical Idle, official atlases and running App remain unchanged.

## Evidence

`assets/rework/v0.1.0/gu-drag-side-shuffle-keyposes-2026-10-01/qa-native-readiness/`

- `idle-vs-keyposes.gif`: four poses, source order, 250 ms each, infinite loop.
- `idle-vs-keyposes-slow.gif`: same four poses, 500 ms each.
- `idle-vs-keyposes-contact.png`: canonical Idle beside every pose.
- `idle-pose-01-overlay.png` through `04`: 50% opacity inspection overlays.
- `validation.json`: reproducible source/preview measurements and transforms.

Idle is a reference panel, not an additional animation frame. All candidates
use one common 0.3 nearest-neighbor **review scale**, with head-band centering
and a common vertical offset matching the source's visible foot line to Idle.
The registration x=96 is not replaced by bbox centering in any runtime asset.
The review includes the entire source-cell extent, including faint alpha haze.
The original-position GIF remains in `qa-motion/`. GIF palette conversion and
the opaque gray background apply only to review media, never source PNGs.

## Proposed next art step — requires user review

Keep the approved four-pose choreography as a motion guide. Derive new native
192×208 candidates from canonical Idle pixels, locking the head, glasses,
hair and upper body, with controlled local leg/shoe editing for the shuffle.
This is an art-production change, not automatic size normalization. Do not
claim its visual quality before it is made and reviewed. Provide GIF, contact
sheet and changed-region evidence before making eight frames or a left version.

If local edits create malformed limbs or pasted joints, stop for human review.
Do not reuse retired E/K/F transition material or relax the Idle contract.
