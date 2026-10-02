# Gu rightward shuffle with upper-body follow-through

Status: `TECHNICAL_PASS_VISUAL_REVIEW_PENDING`.

The earlier selected four-pose animation remains the motion reference. V2 used
its clearer foot trajectory but left the upper body static. In v3 the head,
shoulders, jacket and hanging arms shift together by at most two native pixels
as weight moves toward the screen-right planted foot and returns. The feet
retain the exact v2 RGBA pixels and y=203 contact. There is no whole-sprite
translation. This is a restrained torso sway, not an independent arm swing.

All upper-body pixels are copied directly from formal Gu Idle with integer
translation: no change to face, glasses, hair, body proportions, palette or
pixel cluster colors. The upper segment remains rigid, which avoids the
deformed cuffs and hands found in rejected local sleeve-motion experiments.
Those experiments are retained only in ignored `.cache/` QA, not as candidates.
No generated source pixels are used. User-selected source PNG remains intact.

Review media:

- `qa/running-right-preview.gif`: 8 frames, alternating 120/130 ms, 1 s loop.
- `qa/running-right-slow.gif`: 8 frames, 250 ms each.
- `qa/before-after-motion.gif`: left v2, right v3, same original frames/order/timing.
- `qa/contact-sheet.png`: every current frame.
- `qa/upper-body-detail-contact.png`: 4× shoulder, cuff and hand inspection.
- `qa/before-after-contact.png`: static comparison with v2.
- `qa/validation.json`: per-frame offsets and mechanical checks.

GIFs are uniformly 2× nearest-neighbor on a neutral review background. The
native 1536×208 strip and individual 192×208 PNGs retain RGBA 0/255 alpha.
The visual review should focus on the torso/hip junction, whether upper-body
motion is sufficient, hand/cuff shape and the 8→1 loop. Mechanical tests do not
replace that judgement. No formal atlas or running App has been changed.
