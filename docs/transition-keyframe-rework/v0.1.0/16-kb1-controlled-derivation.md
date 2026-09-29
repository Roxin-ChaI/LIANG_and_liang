# KB1: bounded local derivation from frozen K3

One KB1 only. Neither K2/K3 nor B nor a standard atlas is edited. No ImageGen,
App integration, Tag or current-version replacement. The user-local-pixel
mandate overrides hatch-pet's normal image-generation route; independent
visual QA is retained because numerical PASS cannot prove a plausible face.

## Recorded pixel operations

- Native192×208 RGBA source pinned to approved K3, not a generated replacement.
- Head/neck/upper-collar reference part [54,4,122,84] is resized **once locally**
  with NEAREST from68×80 to62×74, placed [57,4,119,78]. Hair, face, glasses,
  ears and the existing identity raster move together, not separate repainting.
- Center(88,44)→(88,41): dx0, dy−3. Hair top remains4. This is not a whole
  person fit. Reference part includes neck/collar; not exact skull segmentation.
- Native upper jacket panels60:84 and103:129 move outward by a tapered1–6px
  profile. Same-source edge pixels fill small cloth seams. The upper neck/jacket
  rows meet the smaller reference part at y78, tapering a6px row offset back to
  source rows. No blending, interpolated colors or new palette.
- Screen-left lower-arm/cuff/hand assembly begins a1px inward /1px upward
  movement. Both feet and all y164:208 bytes are unchanged.
- No effects, global translation, scaling, B donor pixels, alpha cleanup,
  artificial landmark padding or bbox-driven whole-person normalization.

Body70:208 hull [60,70,129,204]→[54,70,135,204], width69→81 (+12),
body-band center94.5 unchanged; construction registration96 and sole203.
Head−6/−6, center0/−3, body+12 all satisfy the incoming budget. One connected
character, alpha0/255, no hidden RGB/isolated pixel/clipping/new enclosed holes.
Exact derivation is reproducible from the hash-bound edit plan; undisclosed
face/foot edits fail the gate. Numeric checks alone keep approval pending.

## Evidence and separate gates

`k3-b-bridge/kb1/qa/` contains native/nearest3x contacts, RGBA difference mask,
overlay, measured report and hash-bound independent review/resolution.
The reviewer checks identity, head continuity, neck/collar connection, body
progression, arm attachment, cloth seams, fixed feet, artifacts and incoming
continuity. A missing/stale/failed check blocks the next stage. Independent
static PASS is not user artistic approval or proof KB1→B passes; outgoing B
must be audited separately. Two-bridge capacity warning remains unchanged.

Actual independent reviewer `bridge_static_visual` returned
`K3_KB1_STATIC_PASS` with all nine checks PASS after examining native,
nearest3x and difference evidence. The small head transform retained readable
glasses/face/hair; collar and limbs remained connected. Hash-bound resolution
recomputes the actual pixels rather than accepting the cached numeric report.
KB1 PNG SHA256:
`4d1b307e3e251352d3cc165c95f85009d445f797efd94bfeb28fe682a30cd837`.
Focused specification/derivation regression:25 PASS. No outgoing approval yet.
