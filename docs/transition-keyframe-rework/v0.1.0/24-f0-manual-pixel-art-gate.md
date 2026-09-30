# F0 manual pixel-art draft — KB2→F0 gate

Verdict: **F0_MANUAL_QA_FAIL**. The transition-only Feng pose exists as a
native 192×208 RGBA draft, but it is **not approved or runtime eligible**.
The third-stage F0→Idle audit is **NOT_TESTED** by the phase gate.

## Source-preserving edit and evidence

The draft uses formal Feng Review row 8/frame 4 as an approved pixel donor.
Its face/hair/glasses area (y=0–64) is byte-identical to that frame. Below
the head, the low right sleeve/fist and tailored suit are registered into a
two-arm neutral pose; native trouser/shoe pixels are brought inward with
integer-only placement. Two possible waist-seam repairs are specified in the
recipe. No whole-image generation, global scaling, interpolation, blur or
antialiasing occurs. Neither the Feng atlas nor frozen KB2/B was edited.

Reproducible recipe: `tools/manual_f0_pixel_art.py`. Art and evidence:
`assets/rework/v0.1.0/transition-keyframes/feng-f0/manual-pixel-art/`.
The original first draft is preserved by Git Commit 1; the gate-stage
revision narrows the feet and brings the fists slightly inward. `F0.png` is
the current revision and has SHA256
`9e3a64dd388318fa2d48ca630e71a765e3302093f9ff9c6571f8eadef38b8f84`.

## Landmark gate

Head guides are manually approximate (±3 px), not a segmented anatomical
measurement. They cannot independently certify identity.

| Metric | KB2 | F0 | Single-step change |
| --- | ---: | ---: | ---: |
| Head width×height | 56×68 | 50×55 | −6×−13 px |
| Head center | (88, 38) | (89, 31.5) | (+1, −6.5) px |
| Body-band bbox | (48,70)–(141,204) | (47,70)–(145,204) | width +5 px |
| Body-band center x | 94.5 | 96 | +1.5 px |
| Foot span at y=203 | 72–118 | 71–120 | near aligned |
| Baseline / registration | 203 / 96 | 203 / 96 | unchanged |

Conservative prior single-step guide allows at most 6 px head-size change
and 4 px vertical head-center change. F0 exceeds the height and vertical
center limits. Technical validation confirms native canvas, binary alpha,
transparent RGB zero, reproducible approved-pixel provenance, and no source
changes; these are necessary but not visual approval.

Independent visual review of the revised draft still found a conspicuous
KB2→F0 snap. The narrow foot placement and ground line are improved, but
KB2's hands near the inner thighs jump about 15–20 px outward to F0 fists;
the dark banded jacket becomes a bright fitted Feng suit, and the relaxed
face becomes sharply furrowed in one step. The outgoing F0→B link appears
comparatively coherent *as an advisory visual observation only*: B raises a
hand and widens its stance. It cannot be formally audited until the incoming
link is approved.

The finished Feng identity and the single-step KB2→F0 continuity cannot both
be satisfied by weakening F0 or changing frozen KB2. Another genuinely
hand-edited morphology/arm-pose bridge would require its own scope and
approval. Do not insert this draft into the App, generate a full transition,
or claim `F0_ART_APPROVED`. Whether a separate Feng entry animation is
required remains **UNCONFIRMED** pending a passed incoming gate and then the
formal F0→Idle pose audit.
