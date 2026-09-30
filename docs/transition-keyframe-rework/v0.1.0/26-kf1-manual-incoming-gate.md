# KF1 manual construction and incoming gate

**KB2→KF1 VISUAL PASS**, bound to KF1 PNG SHA256
`c189516b94db095e71a83460c7f2e831ca44841a6c97564f48252445ade1407b`.
This permits KF2 construction; it does not approve the full bridge or F0.

The explicit native-pixel recipe is `tools/manual_kf1_pixel_art.py`. KF1 uses
KB2 hair/face/glasses pixels, removing two selected source columns and four
selected rows locally. No eye/expression redraw occurs. The neckline/cloth
rows move upward with a bounded taper, while ankles/feet from y164 are exact
KB2 bytes. Forearms shift left (−5,−2) / right (+5,−3). A small declared cloth
palette and upper-panel brushes begin the Feng lapel change. Two shirt/sleeve
seams and the vacated elbow region are repaired with native cloth pixels and
explicit outline edits. The recorded recipe contains every region and swatch.

| Guide | KB2 | KF1 | Change |
| --- | --- | --- | --- |
| Head | 56×68 / center(88,38) | 54×64 / center(88,36) | −2×−4; (0,−2) |
| Body-band width | 93 | 95 | +2 |
| Left hand skin center | (80,146.5) | (75,144.5) | (−5,−2) |
| Right hand skin center | (111,151.5) | (116,148.5) | (+5,−3) |
| Sole / registration | 203 / 96 | 203 / 96 | unchanged |

Manual head guides approximate anatomy. Body width includes arms, and hand
skin bounds omit dark outlines. The independent reviewer checked native and
nearest-3x art, overlay and difference mask in addition to the metrics. It
found a modest attached-arm movement, the same neutral face and a gradual
clothing onset. The right sleeve's boxy outer ledge remains a visual warning;
it is connected and inherited from KB2, not an alpha seam.

The technical checks confirm exact recipe reproduction, binary alpha, zero
transparent RGB, one connected body, no isolated pixel/clipping, no new
interior alpha hole, baseline203, registration96 and locked feet. Evidence is
in `assets/rework/v0.1.0/transition-keyframes/feng-f0/morph-bridge/kf1/`.
Frozen KB2/F0 and both standard atlases were left unchanged. No App or player
integration was performed.
