# Formal Feng atlas neutral-pose inventory

Read-only source: `assets/builds/feng/spritesheet.webp`, SHA256
`d697e573268b66cb0f6a062480ec87c8c11712ca34b57f8c2fc0a97ed6e2164a`.
The complete 1536×2288 RGBA v2 atlas was scanned as all 88 actual 192×208
slots, not just selected decoded row strips. There are **74 populated frames**
and **14 transparent unused slots**. Every populated frame has safe canvas
margins; 71 have sole baseline y=203. The other three have y=202/y=200 in
the jumping row, consistent with its small vertical motion. The v2 neutral
slot (idle row 0, frame 6) is populated and was included separately from
the six looping Idle frames.

The immutable per-slot inventory includes row/frame, raw-RGBA digest,
alpha/body bounding boxes, sole baseline, body-band center proxy, nominal
x=96 atlas registration, and an *upper-region* alpha box. The latter is
**not a segmented head**: a raised hand or shoulder may enter y0:70. Manual
head guides and independent visual judgment are required for shortlisted
poses. A numerical center can differ from the nominal atlas anchor when a
limb sticks out; it does not prove the source was translated.

## Visual family observations, not ranking

- Idle 0–6, Failed, Waiting, task Running, Jumping and most Look frames keep
  Feng's complete finger-to-chin pose and wide stance. They are valid formal
  animation frames but are not automatically neutral endpoints.
- Review 2–4 progressively lower the screen-left hand from chin toward chest
  and waist while retaining the frontal Feng face and suit. The legs remain
  in the established wide Idle stance; hand and torso registration require
  closer comparison with KB2 and B.
- Running-right and running-left put both hands low, but turn/lean the head
  and body into directional drag motion. Their feet enter crossed or stepping
  positions, which may introduce a different pose discontinuity.
- Waving removes the chin touch but raises the hand; it is a gesture rather
  than a neutral finishing stance.

These observations identify frames worth *ranking*, not approved F0s. No
atlas frame was copied, modified, translated, rescaled, or installed. The
full inventory and labeled native-pixel Contact Sheet are under
`assets/rework/v0.1.0/transition-keyframes/feng-f0/atlas-neutral-audit/`.
The next stage must choose at most three candidate cells and document each
one's head/body guides, baseline/registration, hand/leg pose and both
KB2→candidate and candidate→formal Feng Idle visual differences. A visually
inappropriate pose cannot be rescued by a favorable bbox.
