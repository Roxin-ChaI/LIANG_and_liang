# F0-v2 manual construction

The candidate is derived directly from KF2, with no retired-F0 or B pixel donors. Its construction recipe is `tools/manual_f0_v2.py`; all approved source hashes are checked before reading them.

Output: `assets/rework/v0.1.0/transition-keyframes/feng-f0/v2/candidate/F0-v2.png` (192×208 RGBA).

## Preserved pixels

The 43×28 facial expression crop is byte-identical after a rigid 2px upward placement. Both hand/cuff rectangles remain byte-identical at their existing positions. The complete y≥192 foot band remains byte-identical, including transparent RGB/alpha. Source glasses, eyebrows, eyes, nose and mouth retain their existing expression.

## Local construction

- Remove two selected outer-hair columns and four selected hair/neck rows; no entire-person scaling. Head guide becomes 50×55 from 52×59, center (88,31.5) from (88,33.5).
- Lift collar/upper-torso pixels in explicit 4/3/2/1px bands; add one native pixel to the shoulder caps. Body-band bbox becomes `[46,70,147,204]`, width 101, versus KF2 width 100.
- Consolidate the basic central blue jacket using KF2 swatches, preserve lapels and arm attachment, draw two explicit 1px side seams.
- Strengthen the existing straight trouser outlines by up to three native columns, tapering to zero before the feet. Fill the specifically identified right-thigh insertion seam using adjacent same-row fabric pixels. Preserve the existing stance and inner leg gap.
- Reapply expression, hands and feet locks last. No sharp Feng face replacement, new arm pose, wide stance or deep folded-trouser donor.

## Evidence and limits

The candidate directory contains native and nearest-3x Contact Sheets, a QA alpha overlay, difference mask, semantic-change mask/legend, landmark/lock report and complete pixel-edit provenance. Overlay blending is QA-only; the candidate has binary alpha, zero hidden RGB, source-only colors, one connected character and no new interior alpha holes.

The semantic-change mask classifies changed coordinates into head, upper suit and pants. It is not an automatic claim about expression or identity. Those are reviewed in the next gate, independently of the geometry result. The construction commit does not approve Morph or authorize Entry.
