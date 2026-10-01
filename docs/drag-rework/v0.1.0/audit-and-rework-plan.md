# Gu/Feng drag rework — source audit, not art approval

## Scope

User rejected both drag directions. This audit reviews 32 formal atlas frames
and their Idle references. No source pixels, runtime, Scheduler, Hooks or live
application were changed. The six eye-repair candidates remain pending explicit
visual approval; a request to continue is not an art approval.

## Confirmed mechanical findings

- Gu and Feng each use eight frames per direction, rows 1/2 respectively.
- All 32 sole baselines are y=203. A blanket vertical translation would not
  address this reported drag issue.
- Each form's left frame is pixel-identical to the same-index right frame's
  horizontal mirror (8/8 matches each). The strips were not mirrored as a whole;
  there is no frame-order reversal. Mirroring propagates right-source defects.
- Current renderer maps positive dx>=4 to right and negative dx<=-4 to left.
  The tested direction names are not swapped.
- **Interaction issue reproduced:** twelve successive +1 px (or -1 px) events
  call moveBy twelve times but never send a drag-state event. Direction threshold
  is evaluated per pointer event, while the previous pointer position is updated
  every time. Small moves do not accumulate toward the threshold.
- These interaction results execute the actual project renderer in a deterministic
  VM harness. They are NOT actual mouse or live-window acceptance results.

## Visual observations, requiring human acceptance of replacements

- Gu right frames 02/03/04/06/08 repeat a similar crossed/bent leg silhouette.
  Frames 01/05/07 use a more extended leg. The resulting poses do not clearly
  establish the requested readable alternating foot-contact cycle. This does not
  prove anatomical left/right leg identity from a silhouette alone.
- Gu's recurring tilted head/upper body needs direct continuity review against
  the canonical upright Idle. Being passively dragged can justify a lean; a lean
  alone is not proof that the direction is wrong.
- Feng drag has a strongly angled, narrower-looking face/head and a different
  jacket/body silhouette than canonical Idle. Some contour change is normal
  for turning; identity/style consistency still fails the user's stated visual
  acceptance and cannot be established by equal overall height/bbox.
- The existing QA booleans are historical results, not authority to overrule
  this newer human rejection. Current status: `DRAG_ART_REWORK_REQUIRED`.

## Proposed art work order

1. Develop four readable rightward key poses per form: weight shift, first foot
   contact, passing/transfer, opposite foot contact. Show beside canonical Idle.
2. Preserve Idle face/hair/glasses design, palette, pixel scale and body proportions.
   Do not reuse the retired barrel-shoulder/limb-compositing workflow.
3. Gu: small delayed passive steps; Feng: controlled stable steps. Neither is
   sprinting. The movement must read without speed lines or enlarged gestures.
4. Human approval of the key poses precedes eight-frame completion. Validate each
   foot's contact/lift/return and 08→01 continuity separately from body bbox.
5. Derive/review left only after right is approved. Per-cell mirroring is a possible
   technique, not proof that identity and posture remain acceptable.
6. Keep interaction-trigger repair separate from art. A future fix should handle
   accumulated slow motion and direction-change hysteresis; it must not silently
   modify frozen transition logic or the current running App.

No new drag art has been generated or approved by this audit. No live mouse test
was performed. The current original atlas and all frozen reverse frames remain intact.

## Evidence

`evidence/gu-idle-drag-contact.png` and `feng-idle-drag-contact.png` contain Idle
plus all 16 drag frames per form. Four `*-with-idle.gif` files show a reference
Idle, eight drag frames (120 ms, final frame 220 ms), then Idle. GIF backgrounds
and palette conversion are preview-only, not edits to source art.

`evidence/inventory.json` records exact hashes, mirror comparisons and alpha
bounding boxes. These are not segmented anatomical measurements.
`evidence/interaction-probe.json` records all four deterministic interaction cases.
