# Gu native Idle-pixel shuffle — v1 candidate

Status: `FOUR_KEYPOSES_HUMAN_APPROVED`. Not runtime material.
The user approved this rendering with “审核通过进入下一步”. Approval is bound
to the four PNG hashes in `human-approval.json`. The generated QA report below
is retained as a historical pre-approval record.

The user approved the previous four-pose motion concept, the proposal to derive
native pixels from canonical Idle, and finally these four rendered keyposes.
It is not an eight-frame animation; new in-betweens require their own review.

## What changed

All pixels in rows 0–160 inclusive are byte-identical to canonical Gu Idle.
This locks hair, face, glasses, neck, torso, arms and hands, with no repositioning.
Only lower-leg and shoe pixels below that boundary are moved. Source is exactly
`assets/rework/v0.1.0/idle-appearance-contract-2026-10-01/gu-idle-native.png`.
No generated draft pixels or retired transition pixels are used.

The editable lower legs are separated at the transparent gap x=97. Every source
row receives an integer horizontal offset gradually increasing toward the ankle.
Lifting the foot by two pixels overlaps two source shin rows: lower rows win.
This is disclosed local pixel editing, not lossless relocation of every source
pixel. There is no whole-body or per-frame scaling, rotation, interpolated color,
antialiasing, palette replacement or AI generation. Shoes retain their source
silhouette through rigid integer translation; all retained RGBA pixels come from
Idle. Exact row-level provenance and overlaps are in `qa/validation.json`.

| Pose | Screen-left foot | Screen-right foot |
| --- | --- | --- |
| 1 | support at original position | +1 px right, 2 px up |
| 2 | support at original position | +5 px right, grounded |
| 3 | +3 px right, 2 px up | +5 px right, support |
| 4 | +1 px right, grounded | +2 px right, grounded |

Foot contact remains y=203; the body keeps its original logical anchor x=96.
The alpha bbox center is not used to recenter the character. No canvas clipping,
isolated 8-connected components, partial alpha or hidden transparent RGB was
found. Bbox variation of up to 2 px in overall width reflects the moving shoe.

## Review limitations

- Pose 1 lifts the whole foot slightly instead of the draft's heel articulation.
- Upper body is intentionally fixed, with no lean or weight-transfer redraw.
- These four sparse poses cannot establish the eventual eight-frame gait.
- Small shin-row overlaps need visual review for cuff/knee creases; connectivity
  and unchanged head pixels do not certify anatomy or fluid motion.
- Motion magnitude and pose 4→1 return still require user approval.

## Deliverables

- `pose-01.png`–`pose-04.png`: 192×208 RGBA.
- `keyposes.png`: 768×208 RGBA, same pose order.
- `qa/idle-vs-keyposes.gif`: four poses, 250 ms each, loop forever.
- `qa/idle-vs-keyposes-slow.gif`: four poses, 500 ms each.
- `qa/contact-sheet.png`: Idle beside each candidate.
- `qa/legs-contact-sheet.png`: Idle plus all lower-leg poses at 4× nearest.
- `qa/difference-*.png`: every changed pixel marked, no hidden changes.
- `qa/overlay-*.png`: 50% alpha comparison for review only.
- `qa/locked-region-mask.png`, `qa/validation.json`: lock and provenance.

Main review GIF displays both canvases at exactly 2× nearest-neighbor, without
additional alignment. Static Idle is a reference panel, not a fifth frame.
Gray background and shared palette conversion are GIF-preview limitations only;
native PNGs retain original RGBA. No left version, additional frames, atlas edits
or App integration have been made. Frozen sources remain untouched.
