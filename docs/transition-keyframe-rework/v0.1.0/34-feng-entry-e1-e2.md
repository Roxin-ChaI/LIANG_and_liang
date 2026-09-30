# Feng Entry E1/E2 local pixel art

The first two Entry frames are native 192×208 RGBA. E1 and E2 use F0-v2 as a checked source. The left forearm is repositioned as an explicitly masked part with nearest native pixels; documented flat-palette elbow stitches close local seams. The rest of the character is not rotated or scaled. Selected eyebrow pixels tighten gradually. E2 moves the left leg outward 8px from a fixed hip, while the right shoe stays planted; the right hand/cuff moves slightly and two local rows are removed to begin a clenched shape.

Source files, local mask/angle/row edits, hand/foot bounds and all technical checks are stored in `assets/rework/v0.1.0/transition-keyframes/feng-f0/v2/feng-entry/e1-e2/`. The file contains native and nearest-3x Contact Sheets and F0-v2→E1 / E1→E2 overlays. A directly inspected visual review is hash-bound to both candidate PNGs and the F0-v2 anchor.

F0-v2→E1: the hand moves upward approximately 12px; the first brow pixels change while both feet remain grounded. E1→E2: the hand rises around 21px more toward the chest, the other hand begins to close, and one foot steps outward 8px. The head guide stays 50×55, baseline y=203 and x registration=96. Alpha is binary, transparent RGB is zero, and source foot/hand silhouette is not clipped.

The verdict `ENTRY_E1_E2_STATIC_PASS` permits E3 construction. It is a project static image gate, not human approval or runtime motion validation. The inherited angular outer sleeve remains visible and must be reviewed again in the full Entry chain; this gate does not waive that concern.
