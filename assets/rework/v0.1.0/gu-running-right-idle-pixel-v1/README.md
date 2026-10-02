# Gu rightward shuffle: eight-frame review candidate

Status: `TECHNICAL_PASS_HUMAN_REVIEW_PENDING`.

The user approved the native four-pose candidate from commit `0cc2c0a` with
“审核通过进入下一步”. That approval is recorded beside the original keyposes
and bound to their four PNG SHA256 values. It does not approve this new cycle.

Approved poses 1–4 occupy frames **1, 3, 5, 7**, byte-identically and in the same
order. Frames 2, 4, 6, 8 are new. They reuse the approved canonical-pixel method:
integer lower-leg row displacement, with row overlap for lifted shins. No
ImageGen, whole-body scaling, color interpolation or new source colors.

| Frame | Screen-left foot dx / lift | Screen-right foot dx / lift | Source |
| --- | --- | --- | --- |
| 1 | 0 / 0 | 1 / 2 | approved key 1 |
| 2 | 0 / 0 | 3 / 1 | new |
| 3 | 0 / 0 | 5 / 0 | approved key 2 |
| 4 | 1 / 1 | 5 / 0 | new |
| 5 | 3 / 2 | 5 / 0 | approved key 3 |
| 6 | 2 / 1 | 3 / 0 | new |
| 7 | 1 / 0 | 2 / 0 | approved key 4 |
| 8 | 0 / 0 | 1 / 1 | new |

Screen directions are not anatomical left/right labels. No mirroring occurred.
All adjacent pairs, including 8→1, change foot offsets by at most 2 px
horizontally and 1 px vertically. This is a geometric check, not visual approval.
One foot remains grounded at y=203 in every frame. Logical x registration stays
96 through unchanged canonical upper-body coordinates, not bbox recentering.

Rows 0–160 remain byte-identical to Idle. This preserves hair, face, glasses,
neck, torso, arms and hands. All eight images are 192×208 RGBA with binary alpha,
source-only colors, zero hidden RGB, a single 8-connected foreground component,
and clear cell borders. These checks do not certify natural anatomy or gait.

## Review media

- `running-right.png`: 1536×208 candidate strip.
- `frame-01.png`–`frame-08.png`: independent native images.
- `qa/running-right-preview.gif`: 8 frames, alternating 120/130 ms; 1 s loop.
- `qa/running-right-slow.gif`: 8 frames, 250 ms each; 2 s loop.
- `qa/idle-vs-running-right.gif`: static Idle beside the same eight-frame loop.
- `qa/contact-sheet.png`: all eight full frames, labeled new/approved.
- `qa/legs-contact-sheet.png`: lower legs enlarged 4× nearest-neighbor.
- `qa/difference-*.png`: every adjacent pair including 8→1.
- `qa/validation.json`: provenance, geometry, comparison and timing records.

The 120/130 ms cadence reflects GIF's 10 ms timing increments while retaining
the approved 250 ms key-to-key spacing. This is review timing, not a runtime
configuration change. GIF uses an opaque gray background and one quantized
palette; PNGs preserve exact RGBA. Main previews are uniformly 2× nearest,
without alignment or hidden frames. Idle is a reference panel, not a ninth frame.

Human review must check shin/cuff creases, visible foot sliding during return,
the deliberately fixed upper body, readable rightward dragging and 8→1 rhythm.
No full-cycle approval is inferred from the four approved poses.

No leftward version, frozen-asset change, official atlas write or App integration.
