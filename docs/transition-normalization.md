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

Final alpha bboxes are `(left, top, right-exclusive, bottom-exclusive)`.
These runtime-only SHA256 values are also frozen verbatim in
`assets/transform-runtime.sha256`:

| Direction | Frame | Final bbox | SHA256 |
| --- | ---: | --- | --- |
| Gu→Feng | 01 | (64, 45, 129, 204) | 281a9ce09dbbdb07accdc853b094d9873ef4135d3426a4ff6963df7395bb5146 |
| Gu→Feng | 02 | (52, 34, 141, 204) | 762acb06455fc6bca41a3baafb595f23201bd055997fa64d0bbe7043708993f8 |
| Gu→Feng | 03 | (7, 25, 185, 204) | 84596402015b5f0def103960ca570677f2a68d4e573dfa9491728bd37b189c88 |
| Gu→Feng | 04 | (12, 18, 180, 204) | 507babfc99455e363870cc2fdd64b7de21e6ae3fe173f9f441869d12595f1276 |
| Gu→Feng | 05 | (8, 18, 185, 204) | 52057c5ee1b94b17c236b1e39b41c7077847fcf90628d854ee07c4e724f7accf |
| Gu→Feng | 06 | (13, 18, 179, 204) | da25465f78ef56bca2ca41c093b9369c13168a873b3046334e2be09db082b02e |
| Gu→Feng | 07 | (4, 16, 187, 204) | 13f95b95a37591484f1955897a047007d1a89b43ce546efbf52600fdf1863bd0 |
| Gu→Feng | 08 | (31, 19, 161, 204) | cc8ebb3cbeb3c2d92900bbe2ebebf9180830e04a5ac592b33fad0b93932e11d9 |
| Gu→Feng | 09 | (8, 19, 185, 204) | 0d9a5b8678dccc73c27af597f95c6adf5f157137e17234693bd2ad8dfc579b0b |
| Gu→Feng | 10 | (25, 21, 167, 204) | 7ef83cf405edb8c5d3f33a6e50cf59f1aeb6ab27ec60a0320b2920eedbb4e929 |
| Feng→Gu | 01 | (24, 21, 168, 204) | 0972e1c23065f0bea2178ab73783408da50362b2b7f0802aecfd8f4939844100 |
| Feng→Gu | 02 | (13, 22, 179, 204) | f54490450368482684db53ca4430436391548d060bfe5555f71fa311bc34ea67 |
| Feng→Gu | 03 | (35, 23, 157, 204) | 894e3550da65daa9f2408b5b501451062db5ae4d268d6589f249c0b69e185e0b |
| Feng→Gu | 04 | (38, 23, 155, 204) | 6e0b322d2ab6ef34a22c895c828b52ec542c7d0c6adb7b53228ba2e98e020817 |
| Feng→Gu | 05 | (20, 32, 172, 204) | 71831a3c29ce58a041f248ebf041202663954ad291de598bfccd113aca66b7c8 |
| Feng→Gu | 06 | (56, 35, 136, 204) | d49c579b573f3fe1792d24cb2a2c04d08b17cb724492c74adbf1a1bbd105570a |
| Feng→Gu | 07 | (40, 23, 152, 204) | cd9b2fd76ebe751cbff3d342fddfc67330b185f9d40fbb1e9da5e46b9f464fa3 |
| Feng→Gu | 08 | (38, 35, 155, 204) | b79750442a362dada2af2a15f54ff9957e4ea3e3d24e7bc88cbcdfa25b706e2f |

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
