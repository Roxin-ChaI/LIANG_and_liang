# Phase 3A — transition runtime normalization

The approved 1254×1254 RGBA source PNGs remain in `assets/transform/` and are
frozen by `assets-frozen.sha256`. Only deterministic runtime derivatives are
written to `assets/transform-runtime/`. Filenames and direction-specific frame
order are unchanged. There is no ImageGen, repaint, color replacement, blur,
or interpolation.

## Geometry and method

The formal Gu and Feng v2 idle cells in `assets/builds/{gu,feng}/spritesheet.webp`
both have alpha bounding boxes ending at y=203 (exclusive bottom 204); their
top is y=4. Therefore the shared runtime alpha baseline is y=203. The 192×208
cell center is x=96. Both source sequences are 1254×1254; their effects nearly
fill the source square. The sequence-wide union bounds determine a conservative
188×188 whole-source resize, exactly 188/1254 = 0.149920255... in both axes.
The same single nearest-neighbor scale applies to every frame, and in fact to
both directions. The resized frame's nonzero-alpha bbox is cropped, then that
bbox is centered horizontally and placed with its bottom alpha row at y=203.
Positioning uses integer coordinates only. A 2 px left/right margin is reserved
for the widest possible resized content; the top stays clear of the cell edge.

This alpha-bbox registration preserves every nearest-neighbor-sampled source
pixel but cannot distinguish shoes from effect pixels. In effect-heavy frames,
the visible shoe sole can therefore sit above y=203 even though the nonzero
alpha baseline is stable. Original antialiased/translucent source pixels also
remain translucent; normalization does not introduce new interpolation.

| Direction | Frames | Source | Union bbox | Runtime | Uniform scale | Baseline |
| --- | ---: | --- | --- | --- | ---: | ---: |
| Gu→Feng | 10 | 1254×1254 RGBA | (0, 0, 1240, 1254) | 192×208 RGBA | 188/1254 | 203 |
| Feng→Gu | 8 | 1254×1254 RGBA | (0, 9, 1218, 1254) | 192×208 RGBA | 188/1254 | 203 |

## QA disposition

`VISUAL_REVIEW_REQUIRED` is true. The original transition artwork includes
large effects and endpoint character proportions that cannot be made identical
to the formal atlas entry frame by the permitted crop/one-scale/translation
operations alone. This is an endpoint visual continuity warning, not permission
to repaint or alter approved source art. Phase 3 must review the runtime
one-shot rendering visually before adopting these derivatives.

The normalized Gu→Feng first frame's alpha height is 159 px versus 200 px
for the formal Gu idle entry; its final frame is 183 px versus 200 px for
formal Feng idle. Feng→Gu starts at 183 px versus 200 px for formal Feng idle
and ends at 169 px versus 200 px for formal Gu idle. These are material visual
jumps; uniform scaling must not be broken to hide them.

The source hashes are recorded in the existing `assets-frozen.sha256`; Phase 3A
validator verifies all 18 original transition paths against that immutable
baseline. Runtime-only hashes are separately frozen in
`assets/transform-runtime.sha256` after both sequences are complete.

## Freeze result

`NORMALIZATION_PASS`: all 18 runtime PNGs are 192×208 RGBA, nonempty, have
alpha baseline y=203, centered alpha bboxes at x=95.5–96.5, at least 2 px
horizontal edge clearance, clean RGB under fully transparent pixels, hashes
matching the runtime-only manifest, and byte-for-byte deterministic
regeneration. All 18 originals still match `assets-frozen.sha256`.

`VISUAL_REVIEW_REQUIRED = true`: the approved source effects and endpoint
character sizes create visible entry/exit scale discontinuities. This warning
does not invalidate structural normalization, but it blocks silently treating
the derivatives as visually seamless Phase 3 transition assets.
