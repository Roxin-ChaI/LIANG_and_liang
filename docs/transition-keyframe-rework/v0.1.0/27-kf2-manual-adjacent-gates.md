# KF2 manual bridge — final adjacent link failed

Verdict: **MANUAL_BRIDGE_QA_FAIL**. KF1→KF2 passes independent static visual
review. KF2→F0 fails. F0 remains unapproved; the F0→Feng Idle audit cannot run.
Neither approved KF1 nor the retained Feng endpoint was weakened to force PASS.

KF2 is a native 192×208 RGBA pixel recipe in `tools/manual_kf2_pixel_art.py`.
It keeps the KF1 face lineage through two selected column removals and five
selected row removals, with a few explicitly painted brow pixels. It preserves
the earlier body silhouette while adding local retained-F0 lapel/sleeve
fragments, a declared middle-blue palette, hand-painted intermediate elbow
surfaces and partly formed fists. Each fist keeps source F0 pixels with four
selected columns removed. Trouser side strips grow one pixel, the original
negative space between the legs and soles are retained. Source maps, donor
boxes, palette, polygons and every individual seam repair are recorded.

KF2 PNG SHA256:
`1917e459ee6554d29625649c15a87edd7f4029b42338a8645304cab5fa847676`.

| Link | Head size delta | Head center delta | Body-band width | Hand center deltas left / right | Visual |
| --- | --- | --- | --- | --- | --- |
| KF1→KF2 | −2×−5 | (0,−2.5) | +5 | (−6,−1.5) / (+6,−5.5) | PASS |
| KF2→F0 | −2×−4 | (+1,−2) | −2 | (−5,−1) / (+6,−1) | FAIL |

All poses retain sole203 and registration96. Head guides approximate anatomy;
body-band width includes arms, so a −2px hull difference at the last link is
not evidence of a shrinking torso. Numeric checks pass along with binary
alpha, zero hidden RGB, no clipping/isolated pixels, one connected character
and no accidental interior alpha hole. These checks do not resolve the art.

The independent reviewer found KF1→KF2 continuous in the face, attached arms,
feet and intermediate tailoring. At KF2→F0 the retained relaxed/droopy Gu eyes
and pale glasses become the sharp Feng expression abruptly; the mouth/jaw
and hair also change their visual reading. Thin straight trouser columns become
bulkier folded blue legs while patchwork dark tailoring becomes a finished
bright blue suit in one frame. The final link still concentrates too much
expression, leg volume and cloth finish despite aligned head/hand/foot guides.

Evidence: `assets/rework/v0.1.0/transition-keyframes/feng-f0/morph-bridge/kf2/`.
No further art is generated in this phase after the failed adjacent gate.
The complete chain review records this remaining P1 and cannot approve F0.
